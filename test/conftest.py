import socket
import time
import pytest

HOST = "localhost"
PORT = 6379


def send(sock, *args):
    """Send a RESP command and return the raw response string"""
    cmd = f"*{len(args)}\r\n"
    for arg in args:
        cmd += f"${len(arg)}\r\n{arg}\r\n"
    sock.sendall(cmd.encode())
    return sock.recv(4096).decode()


@pytest.fixture
def conn():
    """A fresh connection per test, auto-closed after"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.settimeout(3)
    yield s
    s.close()


@pytest.fixture
def conn2():
    """A second connection for concurrent/blocking tests"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.settimeout(5)
    yield s
    s.close()


def new_conn():
    """Create a connection manually (for threads)"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.settimeout(3)
    return s