"""Test File"""

import socket
import time
import subprocess
import sys
import os

HOST = "localhost"
PORT = 6379

def send_command(sock, *args):
    """Send a RESP command and return the raw response"""
    cmd = f"*{len(args)}\r\n"
    for arg in args:
        cmd += f"${len(arg)}\r\n{arg}\r\n"
    sock.sendall(cmd.encode())
    return sock.recv(1024).decode()

def new_connection():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.settimeout(2)
    return s

# ─── Test Helpers ────────────────────────────────────────────────────────────

passed = 0
failed = 0

def test(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  ✅ PASS: {name}")
        passed += 1
    else:
        print(f"  ❌ FAIL: {name}")
        print(f"       expected: {repr(expected)}")
        print(f"       actual:   {repr(actual)}")
        failed += 1

# ─── Tests ───────────────────────────────────────────────────────────────────

def test_ping():
    print("\n📦 PING")
    s = new_connection()
    test("PING returns PONG", send_command(s, "PING"), "+PONG\r\n")
    test("ping lowercase", send_command(s, "ping"), "+PONG\r\n")
    test("multiple PINGs", send_command(s, "PING"), "+PONG\r\n")
    s.close()

def test_echo():
    print("\n📦 ECHO")
    s = new_connection()
    test("ECHO hey",        send_command(s, "ECHO", "hey"),    "$3\r\nhey\r\n")
    test("ECHO hello",      send_command(s, "ECHO", "hello"),  "$5\r\nhello\r\n")
    test("ECHO empty",      send_command(s, "ECHO", ""),       "$0\r\n\r\n")
    test("echo lowercase",  send_command(s, "echo", "test"),   "$4\r\ntest\r\n")
    test("ECHO long string",
         send_command(s, "ECHO", "a" * 100),
         f"$100\r\n{'a' * 100}\r\n")
    s.close()

def test_set_get():
    print("\n📦 SET / GET")
    s = new_connection()
    test("SET foo bar returns OK",  send_command(s, "SET", "foo", "bar"),  "+OK\r\n")
    test("GET foo returns bar",     send_command(s, "GET", "foo"),         "$3\r\nbar\r\n")
    test("SET overwrite",           send_command(s, "SET", "foo", "baz"),  "+OK\r\n")
    test("GET after overwrite",     send_command(s, "GET", "foo"),         "$3\r\nbaz\r\n")
    test("GET missing key",         send_command(s, "GET", "nonexistent"), "$-1\r\n")
    test("SET numeric value",       send_command(s, "SET", "num", "42"),   "+OK\r\n")
    test("GET numeric value",       send_command(s, "GET", "num"),         "$3\r\n42\r\n")
    test("SET empty value",         send_command(s, "SET", "empty", ""),   "+OK\r\n")
    test("GET empty value",         send_command(s, "GET", "empty"),       "$0\r\n\r\n")
    s.close()

def test_expiry_px():
    print("\n📦 SET with PX expiry")
    s = new_connection()

    # key should exist before expiry
    send_command(s, "SET", "ex1", "val", "PX", "300")
    test("GET before PX expiry",  send_command(s, "GET", "ex1"), "$3\r\nval\r\n")

    # wait for expiry
    time.sleep(0.4)
    test("GET after PX expiry",   send_command(s, "GET", "ex1"), "$-1\r\n")

    # short expiry
    send_command(s, "SET", "ex2", "hello", "PX", "100")
    test("GET before short expiry", send_command(s, "GET", "ex2"), "$5\r\nhello\r\n")
    time.sleep(0.2)
    test("GET after short expiry",  send_command(s, "GET", "ex2"), "$-1\r\n")

    s.close()

def test_expiry_ex():
    print("\n📦 SET with EX expiry")
    s = new_connection()

    send_command(s, "SET", "exs", "world", "EX", "1")
    test("GET before EX expiry",  send_command(s, "GET", "exs"), "$5\r\nworld\r\n")
    time.sleep(1.1)
    test("GET after EX expiry",   send_command(s, "GET", "exs"), "$-1\r\n")

    s.close()

def test_concurrent_clients():
    print("\n📦 Concurrent clients")
    s1 = new_connection()
    s2 = new_connection()

    send_command(s1, "SET", "shared", "from_s1")
    test("client 2 sees client 1's write", send_command(s2, "GET", "shared"), "$9\r\nfrom_s1\r\n")

    send_command(s2, "SET", "shared", "from_s2")
    test("client 1 sees client 2's write", send_command(s1, "GET", "shared"), "$9\r\nfrom_s2\r\n")

    test("client 1 PING", send_command(s1, "PING"), "+PONG\r\n")
    test("client 2 PING", send_command(s2, "PING"), "+PONG\r\n")

    s1.close()
    s2.close()

def test_case_insensitive():
    print("\n📦 Case insensitivity")
    s = new_connection()
    test("PING uppercase",  send_command(s, "PING"),         "+PONG\r\n")
    test("ping lowercase",  send_command(s, "ping"),         "+PONG\r\n")
    test("Ping mixed",      send_command(s, "Ping"),         "+PONG\r\n")
    test("ECHO uppercase",  send_command(s, "ECHO", "hi"),   "$2\r\nhi\r\n")
    test("echo lowercase",  send_command(s, "echo", "hi"),   "$2\r\nhi\r\n")
    test("EcHo mixed",      send_command(s, "EcHo", "hi"),   "$2\r\nhi\r\n")
    s.close()

# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔌 Connecting to Redis server at localhost:6379...")
    try:
        s = new_connection()
        s.close()
    except ConnectionRefusedError:
        print("❌ Could not connect. Is your server running?")
        sys.exit(1)

    test_ping()
    test_echo()
    test_set_get()
    test_expiry_px()
    test_expiry_ex()
    test_concurrent_clients()
    test_case_insensitive()

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print("💥 Some tests failed.")
    sys.exit(0 if failed == 0 else 1)