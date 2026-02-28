import asyncio
import time

store = {}        # key -> (value, expiry)
list_store = {}   # key -> [list of values]
stream_store = {} # key -> [{"id": "...", "fields": {...}}]

# blocked clients waiting on BLPOP: key -> [(asyncio.Event, result_holder)]
blpop_waiters = {}

def parse_resp(data):
    lines = data.split(b"\r\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(b"*"):
            i += 1
        elif line.startswith(b"$"):
            i += 1
            if i < len(lines):
                result.append(lines[i].decode('utf-8'))
            i += 1
        else:
            i += 1
    return result

def encode_array(items):
    response = f"*{len(items)}\r\n"
    for item in items:
        response += f"${len(item)}\r\n{item}\r\n"
    return response.encode()

def parse_stream_id(id_str):
    """Parse 'ms-seq' into (int, int)"""
    parts = id_str.split("-")
    return int(parts[0]), int(parts[1])

def validate_stream_id(stream_key, id_str):
    """Returns (True, None) if valid, (False, error_msg) if not"""
    ms, seq = parse_stream_id(id_str)
    # 0-0 is always invalid
    if ms == 0 and seq == 0:
        return False, "-ERR The ID specified in XADD must be greater than 0-0\r\n"
    # check against last entry
    if stream_key in stream_store and stream_store[stream_key]:
        last_id = stream_store[stream_key][-1]["id"]
        last_ms, last_seq = parse_stream_id(last_id)
        if ms < last_ms or (ms == last_ms and seq <= last_seq):
            return False, "-ERR The ID specified in XADD is equal or smaller than the target stream top item\r\n"
    return True, None

async def handle_client(reader, writer):
    while True:
        data = await reader.read(1024)
        if not data:
            break

        parts = parse_resp(data)
        if not parts:
            continue

        command = parts[0].upper()

        if command == "PING":
            writer.write(b"+PONG\r\n")

        elif command == "ECHO" and len(parts) > 1:
            arg = parts[1]
            writer.write(f"${len(arg)}\r\n{arg}\r\n".encode())

        elif command == "SET" and len(parts) >= 3:
            key, value = parts[1], parts[2]
            expiry = None
            if len(parts) >= 5:
                option = parts[3].upper()
                if option == "PX":
                    expiry = time.time() * 1000 + int(parts[4])
                elif option == "EX":
                    expiry = time.time() * 1000 + int(parts[4]) * 1000
            store[key] = (value, expiry)
            writer.write(b"+OK\r\n")

        elif command == "GET" and len(parts) >= 2:
            key = parts[1]
            if key in store:
                value, expiry = store[key]
                if expiry is not None and time.time() * 1000 > expiry:
                    del store[key]
                    writer.write(b"$-1\r\n")
                else:
                    writer.write(f"${len(value)}\r\n{value}\r\n".encode())
            else:
                writer.write(b"$-1\r\n")

        elif command == "RPUSH" and len(parts) >= 3:
            key = parts[1]
            elements = parts[2:]
            if key not in list_store:
                list_store[key] = []
            list_store[key].extend(elements)
            # wake any BLPOP waiters
            if key in blpop_waiters and blpop_waiters[key]:
                element = list_store[key].pop(0)
                event, holder = blpop_waiters[key].pop(0)
                holder["key"] = key
                holder["value"] = element
                event.set()
            writer.write(f":{len(list_store[key])}\r\n".encode())

        elif command == "LRANGE" and len(parts) >= 4:
            key = parts[1]
            start = int(parts[2])
            stop = int(parts[3])
            if key not in list_store:
                writer.write(b"*0\r\n")
            else:
                lst = list_store[key]
                length = len(lst)
                if start < 0:
                    start = max(0, length + start)
                if stop < 0:
                    stop = length + stop
                stop = min(stop, length - 1)
                sliced = lst[start:stop + 1]
                if not sliced or start > stop:
                    writer.write(b"*0\r\n")
                else:
                    writer.write(encode_array(sliced))

        elif command == "LLEN" and len(parts) >= 2:
            key = parts[1]
            count = len(list_store.get(key, []))
            writer.write(f":{count}\r\n".encode())

        elif command == "LPOP" and len(parts) >= 2:
            key = parts[1]
            if key not in list_store or len(list_store[key]) == 0:
                writer.write(b"$-1\r\n")
            elif len(parts) == 2:
                # single pop
                element = list_store[key].pop(0)
                writer.write(f"${len(element)}\r\n{element}\r\n".encode())
            else:
                # multi pop
                count = int(parts[2])
                popped = []
                for _ in range(min(count, len(list_store[key]))):
                    popped.append(list_store[key].pop(0))
                writer.write(encode_array(popped))

        elif command == "BLPOP" and len(parts) >= 3:
            key = parts[1]
            timeout = float(parts[2])
            # if element already available, return immediately
            if key in list_store and list_store[key]:
                element = list_store[key].pop(0)
                writer.write(encode_array([key, element]))
            else:
                # block until element available or timeout
                event = asyncio.Event()
                holder = {}
                if key not in blpop_waiters:
                    blpop_waiters[key] = []
                blpop_waiters[key].append((event, holder))
                await writer.drain()
                try:
                    if timeout == 0:
                        await event.wait()
                    else:
                        await asyncio.wait_for(event.wait(), timeout=timeout)
                    writer.write(encode_array([holder["key"], holder["value"]]))
                except asyncio.TimeoutError:
                    # remove from waiters if still there
                    if key in blpop_waiters:
                        blpop_waiters[key] = [(e, h) for e, h in blpop_waiters[key] if e is not event]
                    writer.write(b"*-1\r\n")

        elif command == "TYPE" and len(parts) >= 2:
            key = parts[1]
            if key in store:
                writer.write(b"+string\r\n")
            elif key in list_store:
                writer.write(b"+list\r\n")
            elif key in stream_store:
                writer.write(b"+stream\r\n")
            else:
                writer.write(b"+none\r\n")

        elif command == "XADD" and len(parts) >= 5:
            key = parts[1]
            entry_id = parts[2]
            # parse fields (pairs of key-value after the id)
            fields = {}
            field_parts = parts[3:]
            for i in range(0, len(field_parts) - 1, 2):
                fields[field_parts[i]] = field_parts[i + 1]

            valid, err = validate_stream_id(key, entry_id)
            if not valid:
                writer.write(err.encode())
            else:
                if key not in stream_store:
                    stream_store[key] = []
                stream_store[key].append({"id": entry_id, "fields": fields})
                writer.write(f"${len(entry_id)}\r\n{entry_id}\r\n".encode())

        await writer.drain()

    writer.close()

async def main():
    server = await asyncio.start_server(handle_client, "localhost", 6379)
    async with server:
        await server.serve_forever()

asyncio.run(main())