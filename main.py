import socket
import asyncio

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


#     server_socket = socket.create_server(("localhost", 6379), reuse_port=True)
    
#     while True:
#         connection, _ = server_socket.accept()
#         while True:
#             data = connection.recv(1024)
#             if not data:
#                 break
#             command = data.decode('utf-8')
#             print(f"Received command: {command}")
#             # Basic RESP parsing: check if it's a PING command
#             if "PING" in command.upper():
#                 connection.sendall(b"+PONG\r\n")
#         connection.close()

# if __name__ == "__main__":
#     main()