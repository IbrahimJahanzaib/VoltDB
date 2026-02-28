import socket

def main():

    server_socket = socket.create_server("localhosy", 6379, reuse_port=True)
    server_socket.accept()

if __name__ == "__main__":
    main()
