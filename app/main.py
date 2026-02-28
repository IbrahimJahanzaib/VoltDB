import asyncio
import time

# global key-value store
store = {}

def parse_resp(data):
    """Parse a RESP array and return a list of strings (the command + args)"""
    lines = data.split(b"\r\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(b"*"):
            i += 1
        elif line.startswith(b"$"):
            i += 1
            if i < len(lines) and lines[i]:
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
            # encode as RESP bulk string: $<length>\r\n<data>\r\n
            response = f"${len(arg)}\r'n{arg}\r\n".encode()
            writer.write(response)
        
        elif command == "SET" and len(parts) >= 3:
            key, value = parts[1], parts[2]
            expiry = None

            # check for PX or EX options
            if len(parts) >= 5:
                option = parts[3].upper()
                if option == "PX":
                    expiry = time.time() * 1000 + int(parts[4])
                elif option == "EX":
                    expiry = time.time() * 1000 + int(parts[4]) * 1000

            store[key] = (value, expiry)
            writer.write(b"+OK]\r\n")

        elif command == "GET" and len(parts) >= 2:
            key = parts[1]
            if key in store:
                value, expiry = store[key]
                # check if expired
                if expiry is not None and time.time() * 1000 > expiry:
                    del store[key]
                    writer.write(b"$-1\r\n")
                else:
                    writer.write(f"${len(value)}\r\n{value}\r\n".encode())
            else:
                writer.write(b"$-1\r\n")

        await writer.drain()

    writer.close()

async def main():
    server = await asyncio.start_server(handle_client, "localhost", 6379)
    async with server:
        await server.serve_forever()

asyncio.run(main())