import time
import threading
import pytest
from tests.conftest import send, new_conn


class TestRPush:
    def test_rpush_creates_list(self, conn):
        assert send(conn, "RPUSH", "rp1", "a") == ":1\r\n"

    def test_rpush_appends(self, conn):
        send(conn, "RPUSH", "rp2", "a")
        assert send(conn, "RPUSH", "rp2", "b") == ":2\r\n"

    def test_rpush_multiple_elements(self, conn):
        assert send(conn, "RPUSH", "rp3", "a", "b", "c") == ":3\r\n"

    def test_rpush_multiple_appends(self, conn):
        send(conn, "RPUSH", "rp4", "a", "b")
        assert send(conn, "RPUSH", "rp4", "c", "d") == ":4\r\n"

    def test_rpush_lowercase(self, conn):
        assert send(conn, "rpush", "rp5", "val") == ":1\r\n"


class TestLRange:
    def setup_list(self, conn, key):
        send(conn, "RPUSH", key, "a", "b", "c", "d", "e")

    def test_lrange_full(self, conn):
        self.setup_list(conn, "lr1")
        assert send(conn, "LRANGE", "lr1", "0", "4") == \
            "*5\r\n$1\r\na\r\n$1\r\nb\r\n$1\r\nc\r\n$1\r\nd\r\n$1\r\ne\r\n"

    def test_lrange_partial(self, conn):
        self.setup_list(conn, "lr2")
        assert send(conn, "LRANGE", "lr2", "0", "1") == \
            "*2\r\n$1\r\na\r\n$1\r\nb\r\n"

    def test_lrange_middle(self, conn):
        self.setup_list(conn, "lr3")
        assert send(conn, "LRANGE", "lr3", "2", "4") == \
            "*3\r\n$1\r\nc\r\n$1\r\nd\r\n$1\r\ne\r\n"

    def test_lrange_negative_stop(self, conn):
        self.setup_list(conn, "lr4")
        assert send(conn, "LRANGE", "lr4", "0", "-1") == \
            "*5\r\n$1\r\na\r\n$1\r\nb\r\n$1\r\nc\r\n$1\r\nd\r\n$1\r\ne\r\n"

    def test_lrange_negative_stop_minus2(self, conn):
        self.setup_list(conn, "lr5")
        assert send(conn, "LRANGE", "lr5", "0", "-2") == \
            "*4\r\n$1\r\na\r\n$1\r\nb\r\n$1\r\nc\r\n$1\r\nd\r\n"

    def test_lrange_stop_out_of_bounds(self, conn):
        self.setup_list(conn, "lr6")
        assert send(conn, "LRANGE", "lr6", "0", "100") == \
            "*5\r\n$1\r\na\r\n$1\r\nb\r\n$1\r\nc\r\n$1\r\nd\r\n$1\r\ne\r\n"

    def test_lrange_start_out_of_bounds(self, conn):
        self.setup_list(conn, "lr7")
        assert send(conn, "LRANGE", "lr7", "10", "20") == "*0\r\n"

    def test_lrange_start_greater_than_stop(self, conn):
        self.setup_list(conn, "lr8")
        assert send(conn, "LRANGE", "lr8", "3", "1") == "*0\r\n"

    def test_lrange_missing_key(self, conn):
        assert send(conn, "LRANGE", "nokey_lr", "0", "-1") == "*0\r\n"

    def test_lrange_single_element(self, conn):
        self.setup_list(conn, "lr9")
        assert send(conn, "LRANGE", "lr9", "2", "2") == "*1\r\n$1\r\nc\r\n"


class TestLLen:
    def test_llen_existing(self, conn):
        send(conn, "RPUSH", "ll1", "a", "b", "c", "d")
        assert send(conn, "LLEN", "ll1") == ":4\r\n"

    def test_llen_after_append(self, conn):
        send(conn, "RPUSH", "ll2", "a", "b")
        send(conn, "RPUSH", "ll2", "c")
        assert send(conn, "LLEN", "ll2") == ":3\r\n"

    def test_llen_missing_key(self, conn):
        assert send(conn, "LLEN", "nokey_ll") == ":0\r\n"

    def test_llen_single_element(self, conn):
        send(conn, "RPUSH", "ll3", "only")
        assert send(conn, "LLEN", "ll3") == ":1\r\n"


class TestLPop:
    def test_lpop_single(self, conn):
        send(conn, "RPUSH", "lp1", "one", "two", "three")
        assert send(conn, "LPOP", "lp1") == "$3\r\none\r\n"

    def test_lpop_sequential(self, conn):
        send(conn, "RPUSH", "lp2", "one", "two", "three")
        send(conn, "LPOP", "lp2")
        assert send(conn, "LPOP", "lp2") == "$3\r\ntwo\r\n"

    def test_lpop_count(self, conn):
        send(conn, "RPUSH", "lp3", "one", "two", "three", "four", "five")
        assert send(conn, "LPOP", "lp3", "2") == \
            "*2\r\n$3\r\none\r\n$3\r\ntwo\r\n"

    def test_lpop_count_exceeds_length(self, conn):
        send(conn, "RPUSH", "lp4", "one", "two")
        assert send(conn, "LPOP", "lp4", "100") == \
            "*2\r\n$3\r\none\r\n$3\r\ntwo\r\n"

    def test_lpop_missing_key(self, conn):
        assert send(conn, "LPOP", "nokey_lp") == "$-1\r\n"

    def test_lpop_empty_list(self, conn):
        send(conn, "RPUSH", "lp5", "only")
        send(conn, "LPOP", "lp5")
        assert send(conn, "LPOP", "lp5") == "$-1\r\n"

    def test_lrange_after_lpop(self, conn):
        send(conn, "RPUSH", "lp6", "one", "two", "three")
        send(conn, "LPOP", "lp6")
        assert send(conn, "LRANGE", "lp6", "0", "-1") == \
            "*2\r\n$3\r\ntwo\r\n$5\r\nthree\r\n"


class TestBLPop:
    def test_blpop_element_available(self, conn):
        send(conn, "RPUSH", "bl1", "hello")
        assert send(conn, "BLPOP", "bl1", "1") == \
            "*2\r\n$3\r\nbl1\r\n$5\r\nhello\r\n"

    def test_blpop_timeout(self, conn):
        assert send(conn, "BLPOP", "bl_empty", "0.2") == "*-1\r\n"

    def test_blpop_unblocked_by_rpush(self, conn, conn2):
        # conn blocks on empty list
        cmd = "*3\r\n$6\r\nBLPOP\r\n$4\r\nbl_w\r\n$1\r\n2\r\n"
        conn.sendall(cmd.encode())

        def push_later():
            time.sleep(0.2)
            s = new_conn()
            send(s, "RPUSH", "bl_w", "world")
            s.close()

        t = threading.Thread(target=push_later)
        t.start()
        t.join()
        time.sleep(0.1)

        assert conn.recv(4096).decode() == \
            "*2\r\n$4\r\nbl_w\r\n$5\r\nworld\r\n"