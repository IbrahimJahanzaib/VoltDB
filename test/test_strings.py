import time
import pytest
from tests.conftest import send


class TestPing:
    def test_ping_uppercase(self, conn):
        assert send(conn, "PING") == "+PONG\r\n"

    def test_ping_lowercase(self, conn):
        assert send(conn, "ping") == "+PONG\r\n"

    def test_ping_mixed_case(self, conn):
        assert send(conn, "Ping") == "+PONG\r\n"

    def test_multiple_pings(self, conn):
        assert send(conn, "PING") == "+PONG\r\n"
        assert send(conn, "PING") == "+PONG\r\n"


class TestEcho:
    def test_echo_basic(self, conn):
        assert send(conn, "ECHO", "hey") == "$3\r\nhey\r\n"

    def test_echo_longer(self, conn):
        assert send(conn, "ECHO", "hello") == "$5\r\nhello\r\n"

    def test_echo_empty(self, conn):
        assert send(conn, "ECHO", "") == "$0\r\n\r\n"

    def test_echo_lowercase(self, conn):
        assert send(conn, "echo", "test") == "$4\r\ntest\r\n"

    def test_echo_long_string(self, conn):
        s = "a" * 100
        assert send(conn, "ECHO", s) == f"$100\r\n{s}\r\n"


class TestSet:
    def test_set_returns_ok(self, conn):
        assert send(conn, "SET", "foo", "bar") == "+OK\r\n"

    def test_set_overwrites(self, conn):
        send(conn, "SET", "foo", "bar")
        assert send(conn, "SET", "foo", "baz") == "+OK\r\n"

    def test_set_with_px(self, conn):
        assert send(conn, "SET", "px_key", "val", "PX", "500") == "+OK\r\n"

    def test_set_with_ex(self, conn):
        assert send(conn, "SET", "ex_key", "val", "EX", "10") == "+OK\r\n"


class TestGet:
    def test_get_existing(self, conn):
        send(conn, "SET", "foo", "bar")
        assert send(conn, "GET", "foo") == "$3\r\nbar\r\n"

    def test_get_after_overwrite(self, conn):
        send(conn, "SET", "foo", "bar")
        send(conn, "SET", "foo", "baz")
        assert send(conn, "GET", "foo") == "$3\r\nbaz\r\n"

    def test_get_missing_key(self, conn):
        assert send(conn, "GET", "nonexistent") == "$-1\r\n"

    def test_get_numeric_value(self, conn):
        send(conn, "SET", "num", "42")
        assert send(conn, "GET", "num") == "$2\r\n42\r\n"

    def test_get_empty_value(self, conn):
        send(conn, "SET", "empty", "")
        assert send(conn, "GET", "empty") == "$0\r\n\r\n"


class TestExpiry:
    def test_get_before_px_expiry(self, conn):
        send(conn, "SET", "ex1", "val", "PX", "500")
        assert send(conn, "GET", "ex1") == "$3\r\nval\r\n"

    def test_get_after_px_expiry(self, conn):
        send(conn, "SET", "ex1", "val", "PX", "100")
        time.sleep(0.2)
        assert send(conn, "GET", "ex1") == "$-1\r\n"

    def test_get_before_ex_expiry(self, conn):
        send(conn, "SET", "ex2", "world", "EX", "10")
        assert send(conn, "GET", "ex2") == "$5\r\nworld\r\n"

    def test_get_after_ex_expiry(self, conn):
        send(conn, "SET", "ex3", "world", "EX", "1")
        time.sleep(1.1)
        assert send(conn, "GET", "ex3") == "$-1\r\n"


class TestType:
    def test_type_string(self, conn):
        send(conn, "SET", "strkey", "hello")
        assert send(conn, "TYPE", "strkey") == "+string\r\n"

    def test_type_list(self, conn):
        send(conn, "RPUSH", "listkey", "a")
        assert send(conn, "TYPE", "listkey") == "+list\r\n"

    def test_type_missing(self, conn):
        assert send(conn, "TYPE", "nokey_type") == "+none\r\n"

    def test_type_stream(self, conn):
        send(conn, "XADD", "stkey", "1-1", "f", "v")
        assert send(conn, "TYPE", "stkey") == "+stream\r\n"


class TestConcurrentClients:
    def test_shared_store(self, conn, conn2):
        send(conn, "SET", "shared", "from_s1")
        assert send(conn2, "GET", "shared") == "$7\r\nfrom_s1\r\n"

    def test_overwrite_visible_to_other(self, conn, conn2):
        send(conn, "SET", "shared2", "from_s1")
        send(conn2, "SET", "shared2", "from_s2")
        assert send(conn, "GET", "shared2") == "$7\r\nfrom_s2\r\n"