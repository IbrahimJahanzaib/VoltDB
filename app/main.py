import asyncio
from app.server import handle_client


async def main():
    server = await asyncio.start_server(handle_client, "localhost", 6379)
    print("VoltDB listening on localhost:6379")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())