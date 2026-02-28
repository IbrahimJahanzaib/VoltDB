import asyncio

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
        command = data.decode('utf-8')
        if "PING" in command.upper():
            writer.write(b"+PONG\r\n")
            await writer.drain()
    writer.close()

async def main():
    server = await asyncio.start_server(handle_client, "localhost", 6379)
    async with server:
        await server.serve_forever()

asyncio.run(main())