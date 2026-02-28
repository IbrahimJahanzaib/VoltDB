import asyncio
from app.parser import parse_resp
from app.commands import strings, lists, streams
from app import encoder


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    # per-connection transaction state
    in_multi = False
    queue: list[list[str]] = []

    while True:
        data = await reader.read(4096)
        if not data:
            break

        parts = parse_resp(data)
        if not parts:
            continue

        command = parts[0].upper()

        # ── Transaction control ────────────────────────────────────────────
        if command == "MULTI":
            if in_multi:
                writer.write(encoder.error("ERR MULTI calls can not be nested"))
            else:
                in_multi = True
                queue = []
                writer.write(encoder.simple_string("OK"))
            await writer.drain()
            continue

        if command == "EXEC":
            if not in_multi:
                writer.write(encoder.error("ERR EXEC without MULTI"))
                await writer.drain()
                continue
            # execute all queued commands
            in_multi = False
            responses = []
            for queued_parts in queue:
                resp = await dispatch(queued_parts, writer)
                responses.append(resp)
            # return array of responses
            writer.write(f"*{len(responses)}\r\n".encode())
            for r in responses:
                writer.write(r)
            queue = []
            await writer.drain()
            continue

        if command == "DISCARD":
            if not in_multi:
                writer.write(encoder.error("ERR DISCARD without MULTI"))
            else:
                in_multi = False
                queue = []
                writer.write(encoder.simple_string("OK"))
            await writer.drain()
            continue

        # ── Queue commands if in MULTI ────────────────────────────────────
        if in_multi:
            queue.append(parts)
            writer.write(encoder.simple_string("QUEUED"))
            await writer.drain()
            continue

        # ── Normal dispatch ───────────────────────────────────────────────
        response = await dispatch(parts, writer)
        if response:
            writer.write(response)
            await writer.drain()

    writer.close()


async def dispatch(parts: list[str], writer: asyncio.StreamWriter) -> bytes:
    """Route a command to its handler and return the response bytes."""
    command = parts[0].upper()

    if command == "PING":
        return b"+PONG\r\n"

    elif command == "ECHO" and len(parts) > 1:
        arg = parts[1]
        return f"${len(arg)}\r\n{arg}\r\n".encode()

    elif command == "SET":
        return strings.handle_set(parts)

    elif command == "GET":
        return strings.handle_get(parts)

    elif command == "TYPE":
        return strings.handle_type(parts)

    elif command == "INCR":
        return strings.handle_incr(parts)

    elif command == "RPUSH":
        return lists.handle_rpush(parts)

    elif command == "LRANGE":
        return lists.handle_lrange(parts)

    elif command == "LLEN":
        return lists.handle_llen(parts)

    elif command == "LPOP":
        return lists.handle_lpop(parts)

    elif command == "BLPOP":
        return await lists.handle_blpop(parts, writer)

    elif command == "XADD":
        return await streams.handle_xadd(parts)

    elif command == "XRANGE":
        return streams.handle_xrange(parts)

    elif command == "XREAD":
        return await streams.handle_xread(parts, writer)

    return encoder.error(f"ERR unknown command '{parts[0]}'")