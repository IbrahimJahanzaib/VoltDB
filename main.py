import socket

def main():
    server_socket = socket.create_server(("localhost", 6379), reuse_port=True)
    
    while True:
        connection, _ = server_socket.accept()
        while True:
            data = connection.recv(1024)
            if not data:
                break
            command = data.decode('utf-8')
            print(f"Received command: {command}")
            # Basic RESP parsing: check if it's a PING command
            if "PING" in command.upper():
                connection.sendall(b"+PONG\r\n")
        connection.close()

if __name__ == "__main__":
    main()