import asyncio
from app import store, encoder


def handle_rpush(parts: list[str]) -> bytes:
    if len(parts) < 3:
        return encoder.error("ERR wrong number of arguments for RPUSH")
    key = parts[1]
    elements = parts[2:]
    if key not in store.list_store:
        store.list_store[key] = []
    store.list_store[key].extend(elements)
    # wake any BLPOP waiters
    if key in store.blpop_waiters and store.blpop_waiters[key]:
        element = store.list_store[key].pop(0)
        event, holder = store.blpop_waiters[key].pop(0)
        holder["key"] = key
        holder["value"] = element
        event.set()
    return encoder.integer(len(store.list_store[key]))


def handle_lrange(parts: list[str]) -> bytes:
    if len(parts) < 4:
        return encoder.error("ERR wrong number of arguments for LRANGE")
    key = parts[1]
    start = int(parts[2])
    stop = int(parts[3])
    if key not in store.list_store:
        return encoder.empty_array()
    lst = store.list_store[key]
    length = len(lst)
    if start < 0:
        start = max(0, length + start)
    if stop < 0:
        stop = length + stop
    stop = min(stop, length - 1)
    sliced = lst[start:stop + 1]
    if not sliced or start > stop:
        return encoder.empty_array()
    return encoder.array(sliced)


def handle_llen(parts: list[str]) -> bytes:
    if len(parts) < 2:
        return encoder.error("ERR wrong number of arguments for LLEN")
    key = parts[1]
    return encoder.integer(len(store.list_store.get(key, [])))


def handle_lpop(parts: list[str]) -> bytes:
    if len(parts) < 2:
        return encoder.error("ERR wrong number of arguments for LPOP")
    key = parts[1]
    if key not in store.list_store or len(store.list_store[key]) == 0:
        return encoder.null_bulk_string()
    if len(parts) == 2:
        element = store.list_store[key].pop(0)
        return encoder.bulk_string(element)
    count = int(parts[2])
    popped = [store.list_store[key].pop(0) for _ in range(min(count, len(store.list_store[key])))]
    return encoder.array(popped)


async def handle_blpop(parts: list[str], writer: asyncio.StreamWriter) -> bytes:
    if len(parts) < 3:
        return encoder.error("ERR wrong number of arguments for BLPOP")
    key = parts[1]
    timeout = float(parts[2])

    if key in store.list_store and store.list_store[key]:
        element = store.list_store[key].pop(0)
        return encoder.array([key, element])

    # block
    event = asyncio.Event()
    holder = {}
    if key not in store.blpop_waiters:
        store.blpop_waiters[key] = []
    store.blpop_waiters[key].append((event, holder))
    await writer.drain()
    try:
        if timeout == 0:
            await event.wait()
        else:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        return encoder.array([holder["key"], holder["value"]])
    except asyncio.TimeoutError:
        if key in store.blpop_waiters:
            store.blpop_waiters[key] = [
                (e, h) for e, h in store.blpop_waiters[key] if e is not event
            ]
        return encoder.null_array()