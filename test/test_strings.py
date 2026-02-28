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
        send(conn, "SET", "getkey1", "bar")
        assert send(conn, "GET", "getkey1") == "$3\r\nbar\r\n"

    def test_get_after_overwrite(self, conn):
        send(conn, "SET", "getkey2", "bar")
        send(conn, "SET", "getkey2", "baz")
        assert send(conn, "GET", "getkey2") == "$3\r\nbaz\r\n"

    def test_get_missing_key(self, conn):
        assert send(conn, "GET", "nonexistent_xyz") == "$-1\r\n"

    def test_get_numeric_value(self, conn):
        send(conn, "SET", "numkey", "42")
        assert send(conn, "GET", "numkey") == "$2\r\n42\r\n"

    def test_get_empty_value(self, conn):
        send(conn, "SET", "emptykey", "")
        assert send(conn, "GET", "emptykey") == "$0\r\n\r\n"


class TestExpiry:
    def test_get_before_px_expiry(self, conn):
        send(conn, "SET", "pxkey1", "val", "PX", "500")
        assert send(conn, "GET", "pxkey1") == "$3\r\nval\r\n"

    def test_get_after_px_expiry(self, conn):
        send(conn, "SET", "pxkey2", "val", "PX", "100")
        time.sleep(0.2)
        assert send(conn, "GET", "pxkey2") == "$-1\r\n"

    def test_get_before_ex_expiry(self, conn):
        send(conn, "SET", "exkey1", "world", "EX", "10")
        assert send(conn, "GET", "exkey1") == "$5\r\nworld\r\n"

    def test_get_after_ex_expiry(self, conn):
        send(conn, "SET", "exkey2", "world", "EX", "1")
        time.sleep(1.1)
        assert send(conn, "GET", "exkey2") == "$-1\r\n"


class TestIncr:
    def test_incr_existing_key(self, conn):
        send(conn, "SET", "incrkey1", "5")
        assert send(conn, "INCR", "incrkey1") == ":6\r\n"

    def test_incr_increments_again(self, conn):
        send(conn, "SET", "incrkey2", "5")
        send(conn, "INCR", "incrkey2")
        assert send(conn, "INCR", "incrkey2") == ":7\r\n"

    def test_incr_missing_key_starts_at_one(self, conn):
        assert send(conn, "INCR", "incr_missing_1") == ":1\r\n"

    def test_incr_missing_key_get_after(self, conn):
        send(conn, "INCR", "incr_missing_2")
        assert send(conn, "GET", "incr_missing_2") == "$1\r\n1\r\n"

    def test_incr_non_integer_value(self, conn):
        send(conn, "SET", "incrkey3", "xyz")
        assert send(conn, "INCR", "incrkey3") == \
            "-ERR value is not an integer or out of range\r\n"

    def test_incr_float_value(self, conn):
        send(conn, "SET", "incrkey4", "3.14")
        assert send(conn, "INCR", "incrkey4") == \
            "-ERR value is not an integer or out of range\r\n"


class TestType:
    def test_type_string(self, conn):
        send(conn, "SET", "typestr", "hello")
        assert send(conn, "TYPE", "typestr") == "+string\r\n"

    def test_type_list(self, conn):
        send(conn, "RPUSH", "typelist", "a")
        assert send(conn, "TYPE", "typelist") == "+list\r\n"

    def test_type_missing(self, conn):
        assert send(conn, "TYPE", "nokey_type_xyz") == "+none\r\n"

    def test_type_stream(self, conn):
        send(conn, "XADD", "typestream", "1-1", "f", "v")
        assert send(conn, "TYPE", "typestream") == "+stream\r\n"


class TestConcurrentClients:
    def test_shared_store(self, conn, conn2):
        send(conn, "SET", "shared_cc1", "from_s1")
        assert send(conn2, "GET", "shared_cc1") == "$7\r\nfrom_s1\r\n"

    def test_overwrite_visible_to_other(self, conn, conn2):
        send(conn, "SET", "shared_cc2", "from_s1")
        send(conn2, "SET", "shared_cc2", "from_s2")
        assert send(conn, "GET", "shared_cc2") == "$7\r\nfrom_s2\r\n"


class TestMultiExec:
    def test_multi_returns_ok(self, conn):
        assert send(conn, "MULTI") == "+OK\r\n"

    def test_exec_without_multi(self, conn):
        assert send(conn, "EXEC") == "-ERR EXEC without MULTI\r\n"

    def test_empty_transaction(self, conn):
        send(conn, "MULTI")
        assert send(conn, "EXEC") == "*0\r\n"

    def test_exec_after_empty_transaction_errors(self, conn):
        send(conn, "MULTI")
        send(conn, "EXEC")
        assert send(conn, "EXEC") == "-ERR EXEC without MULTI\r\n"

    def test_commands_queued(self, conn):
        send(conn, "MULTI")
        assert send(conn, "SET", "txkey1", "41") == "+QUEUED\r\n"
        assert send(conn, "INCR", "txkey1") == "+QUEUED\r\n"

    def test_queued_commands_not_executed_until_exec(self, conn, conn2):
        send(conn, "MULTI")
        send(conn, "SET", "txkey2", "hello")
        # before EXEC, key should not exist
        assert send(conn2, "GET", "txkey2") == "$-1\r\n"

    def test_exec_runs_queued_commands(self, conn):
        send(conn, "MULTI")
        send(conn, "SET", "txkey3", "41")
        send(conn, "INCR", "txkey3")
        result = send(conn, "EXEC")
        assert result == "*2\r\n+OK\r\n:42\r\n"

    def test_exec_multiple_sets(self, conn):
        send(conn, "MULTI")
        send(conn, "SET", "txkey4", "a")
        send(conn, "SET", "txkey5", "b")
        assert send(conn, "EXEC") == "*2\r\n+OK\r\n+OK\r\n"

    def test_discard_clears_queue(self, conn, conn2):
        send(conn, "MULTI")
        send(conn, "SET", "txkey6", "value")
        send(conn, "DISCARD")
        # key should not exist
        assert send(conn2, "GET", "txkey6") == "$-1\r\n"

    def test_discard_without_multi(self, conn):
        assert send(conn, "DISCARD") == "-ERR DISCARD without MULTI\r\n"