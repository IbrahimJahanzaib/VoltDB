import asyncio
import time

store = {}       # key -> (value, expiry)
list_store = {}  # key -> [list of values]

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
                    response = f"*{len(sliced)}\r\n"
                    for item in sliced:
                        response += f"${len(item)}\r\n{item}\r\n"
                    writer.write(response.encode())

        elif command == "LLEN" and len(parts) >= 2:
            key = parts[1]
            count = len(list_store.get(key, []))
            writer.write(f":{count}\r\n".encode())

        elif command == "LPOP" and len(parts) >= 2:
            key = parts[1]
            if key not in list_store or len(list_store[key]) == 0:
                writer.write(b"$-1\r\n")
            else:
                element = list_store[key].pop(0)
                writer.write(f"${len(element)}\r\n{element}\r\n".encode())

        await writer.drain()

    writer.close()

async def main():
    server = await asyncio.start_server(handle_client, "localhost", 6379)
    async with server:
        await server.serve_forever()

asyncio.run(main())