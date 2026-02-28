import socket

def main():

    server_socket = socket.create_server("localhosy", 6379, reuse_port=True)
    server_socket.accept()

    connection, _ = server_socket.accept()
    connection.sendall(b"+PONG\r\n")

if __name__ == "__main__":
    main()
