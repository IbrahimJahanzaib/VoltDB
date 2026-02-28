import asyncio
from app.parser import parse_resp
from app.commands import strings, lists, streams


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    while True:
        data = await reader.read(4096)
        if not data:
            break

        parts = parse_resp(data)
        if not parts:
            continue

        command = parts[0].upper()
        response = None

        if command == "PING":
            response = b"+PONG\r\n"

        elif command == "ECHO" and len(parts) > 1:
            arg = parts[1]
            response = f"${len(arg)}\r\n{arg}\r\n".encode()

        elif command == "SET":
            response = strings.handle_set(parts)

        elif command == "GET":
            response = strings.handle_get(parts)

        elif command == "TYPE":
            response = strings.handle_type(parts)

        elif command == "RPUSH":
            response = lists.handle_rpush(parts)

        elif command == "LRANGE":
            response = lists.handle_lrange(parts)

        elif command == "LLEN":
            response = lists.handle_llen(parts)

        elif command == "LPOP":
            response = lists.handle_lpop(parts)

        elif command == "BLPOP":
            response = await lists.handle_blpop(parts, writer)

        elif command == "XADD":
            response = await streams.handle_xadd(parts)

        elif command == "XRANGE":
            response = streams.handle_xrange(parts)

        elif command == "XREAD":
            response = await streams.handle_xread(parts, writer)

        if response:
            writer.write(response)
            await writer.drain()

    writer.close()