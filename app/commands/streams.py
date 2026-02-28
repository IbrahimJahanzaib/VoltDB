import asyncio
import time
from app import store, encoder


# ─── ID Helpers ──────────────────────────────────────────────────────────────

def parse_id(id_str: str) -> tuple[int, int]:
    ms, seq = id_str.split("-")
    return int(ms), int(seq)

def compare_ids(id1: str, id2: str) -> int:
    a = parse_id(id1)
    b = parse_id(id2)
    if a < b: return -1
    if a > b: return 1
    return 0

def resolve_xadd_id(stream_key: str, id_str: str) -> tuple[str | None, bytes | None]:
    """
    Resolves *, ms-*, or explicit ms-seq.
    Returns (resolved_id, None) on success or (None, error_bytes) on failure.
    """
    if id_str == "*":
        ms = int(time.time() * 1000)
        seq = 0
        if stream_key in store.stream_store and store.stream_store[stream_key]:
            last_ms, last_seq = parse_id(store.stream_store[stream_key][-1]["id"])
            if ms == last_ms:
                seq = last_seq + 1
        return f"{ms}-{seq}", None

    ms_str, seq_str = id_str.split("-")
    ms = int(ms_str)

    if seq_str == "*":
        seq = 0 if ms != 0 else 1
        if stream_key in store.stream_store and store.stream_store[stream_key]:
            last_ms, last_seq = parse_id(store.stream_store[stream_key][-1]["id"])
            if ms == last_ms:
                seq = last_seq + 1
            elif ms < last_ms:
                return None, encoder.error("ERR The ID specified in XADD is equal or smaller than the target stream top item")
        return f"{ms}-{seq}", None

    # explicit id validation
    if id_str == "0-0":
        return None, encoder.error("ERR The ID specified in XADD must be greater than 0-0")
    ms_r, seq_r = parse_id(id_str)
    if stream_key in store.stream_store and store.stream_store[stream_key]:
        last_ms, last_seq = parse_id(store.stream_store[stream_key][-1]["id"])
        if ms_r < last_ms or (ms_r == last_ms and seq_r <= last_seq):
            return None, encoder.error("ERR The ID specified in XADD is equal or smaller than the target stream top item")
    return id_str, None

def parse_range_id(id_str: str, default_seq: int) -> str:
    """Fill in missing seq number for XRANGE ids"""
    if "-" in id_str:
        return id_str
    return f"{id_str}-{default_seq}"

def entries_after(stream_key: str, after_id: str) -> list[dict]:
    """Get entries strictly greater than after_id"""
    if stream_key not in store.stream_store:
        return []
    return [e for e in store.stream_store[stream_key] if compare_ids(e["id"], after_id) > 0]


# ─── Waiter notification ─────────────────────────────────────────────────────

async def notify_xread_waiters(stream_key: str):
    if stream_key not in store.xread_waiters:
        return
    still_waiting = []
    for event, holder, after_id in store.xread_waiters[stream_key]:
        new_entries = entries_after(stream_key, after_id)
        if new_entries:
            holder["entries"] = new_entries
            holder["key"] = stream_key
            event.set()
        else:
            still_waiting.append((event, holder, after_id))
    store.xread_waiters[stream_key] = still_waiting


# ─── Command handlers ─────────────────────────────────────────────────────────

async def handle_xadd(parts: list[str]) -> bytes:
    if len(parts) < 5:
        return encoder.error("ERR wrong number of arguments for XADD")
    key = parts[1]
    id_str = parts[2]
    field_parts = parts[3:]
    fields = []
    for i in range(0, len(field_parts) - 1, 2):
        fields.append(field_parts[i])
        fields.append(field_parts[i + 1])

    resolved_id, err = resolve_xadd_id(key, id_str)
    if err:
        return err

    if key not in store.stream_store:
        store.stream_store[key] = []
    store.stream_store[key].append({"id": resolved_id, "fields": fields})

    await notify_xread_waiters(key)
    return encoder.bulk_string(resolved_id)


def handle_xrange(parts: list[str]) -> bytes:
    if len(parts) < 4:
        return encoder.error("ERR wrong number of arguments for XRANGE")
    key = parts[1]
    start_raw = parts[2]
    end_raw = parts[3]

    if key not in store.stream_store:
        return encoder.empty_array()

    start_id = "0-0" if start_raw == "-" else parse_range_id(start_raw, 0)
    end_id = f"{2**63}-{2**63}" if end_raw == "+" else parse_range_id(end_raw, 2**63)

    filtered = [
        e for e in store.stream_store[key]
        if compare_ids(e["id"], start_id) >= 0 and compare_ids(e["id"], end_id) <= 0
    ]
    return encoder.encode_stream_entries(filtered).encode()


async def handle_xread(parts: list[str], writer: asyncio.StreamWriter) -> bytes:
    idx = 1
    block_ms = None

    if parts[idx].upper() == "BLOCK":
        block_ms = float(parts[idx + 1])
        idx += 2

    if parts[idx].upper() == "STREAMS":
        idx += 1

    remaining = parts[idx:]
    mid = len(remaining) // 2
    keys = remaining[:mid]
    raw_ids = remaining[mid:]

    # resolve $ to last entry id
    resolved_ids = []
    for i, k in enumerate(keys):
        if raw_ids[i] == "$":
            if k in store.stream_store and store.stream_store[k]:
                resolved_ids.append(store.stream_store[k][-1]["id"])
            else:
                resolved_ids.append("0-0")
        else:
            resolved_ids.append(raw_ids[i])

    def build_response() -> list[tuple]:
        results = []
        for k, after_id in zip(keys, resolved_ids):
            found = entries_after(k, after_id)
            if found:
                results.append((k, found))
        return results

    result_streams = build_response()

    if result_streams:
        resp = f"*{len(result_streams)}\r\n"
        for stream_key, stream_entries in result_streams:
            resp += f"*2\r\n"
            resp += f"${len(stream_key)}\r\n{stream_key}\r\n"
            resp += encoder.encode_stream_entries(stream_entries)
        return resp.encode()

    if block_ms is not None:
        event = asyncio.Event()
        holder = {}
        for k, after_id in zip(keys, resolved_ids):
            if k not in store.xread_waiters:
                store.xread_waiters[k] = []
            store.xread_waiters[k].append((event, holder, after_id))

        await writer.drain()
        try:
            if block_ms == 0:
                await event.wait()
            else:
                await asyncio.wait_for(event.wait(), timeout=block_ms / 1000)
            k = holder["key"]
            stream_entries = holder["entries"]
            resp = f"*1\r\n*2\r\n"
            resp += f"${len(k)}\r\n{k}\r\n"
            resp += encoder.encode_stream_entries(stream_entries)
            return resp.encode()
        except asyncio.TimeoutError:
            for k, after_id in zip(keys, resolved_ids):
                if k in store.xread_waiters:
                    store.xread_waiters[k] = [
                        (e, h, a) for e, h, a in store.xread_waiters[k] if e is not event
                    ]
            return encoder.null_array()

    return encoder.null_array()