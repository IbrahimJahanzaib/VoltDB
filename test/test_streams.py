import time
import threading
import pytest
from tests.conftest import send, new_conn


class TestXAddExplicit:
    def test_xadd_returns_id(self, conn):
        assert send(conn, "XADD", "xa1", "1-1", "foo", "bar") == "$3\r\n1-1\r\n"

    def test_xadd_second_entry(self, conn):
        send(conn, "XADD", "xa2", "1-1", "foo", "bar")
        assert send(conn, "XADD", "xa2", "2-1", "baz", "qux") == "$3\r\n2-1\r\n"

    def test_xadd_duplicate_id(self, conn):
        send(conn, "XADD", "xa3", "1-1", "foo", "bar")
        assert send(conn, "XADD", "xa3", "1-1", "a", "b") == \
            "-ERR The ID specified in XADD is equal or smaller than the target stream top item\r\n"

    def test_xadd_smaller_ms(self, conn):
        send(conn, "XADD", "xa4", "2-1", "foo", "bar")
        assert send(conn, "XADD", "xa4", "1-5", "a", "b") == \
            "-ERR The ID specified in XADD is equal or smaller than the target stream top item\r\n"

    def test_xadd_zero_zero_invalid(self, conn):
        assert send(conn, "XADD", "xa5", "0-0", "a", "b") == \
            "-ERR The ID specified in XADD must be greater than 0-0\r\n"

    def test_xadd_minimum_valid_id(self, conn):
        assert send(conn, "XADD", "xa6", "0-1", "x", "y") == "$3\r\n0-1\r\n"


class TestXAddAutoSeq:
    def test_auto_seq_starts_at_one_for_ms_zero(self, conn):
        assert send(conn, "XADD", "xas1", "0-*", "foo", "bar") == "$3\r\n0-1\r\n"

    def test_auto_seq_increments(self, conn):
        send(conn, "XADD", "xas2", "0-*", "foo", "bar")
        assert send(conn, "XADD", "xas2", "0-*", "foo", "bar") == "$3\r\n0-2\r\n"

    def test_auto_seq_starts_at_zero_for_nonzero_ms(self, conn):
        assert send(conn, "XADD", "xas3", "5-*", "foo", "bar") == "$3\r\n5-0\r\n"

    def test_auto_seq_increments_same_ms(self, conn):
        send(conn, "XADD", "xas4", "5-*", "foo", "bar")
        assert send(conn, "XADD", "xas4", "5-*", "foo", "bar") == "$3\r\n5-1\r\n"

    def test_auto_seq_new_ms_resets_to_zero(self, conn):
        send(conn, "XADD", "xas5", "5-*", "foo", "bar")
        assert send(conn, "XADD", "xas5", "10-*", "foo", "bar") == "$4\r\n10-0\r\n"


class TestXAddAutoId:
    def test_auto_id_uses_current_time(self, conn):
        before = int(time.time() * 1000)
        resp = send(conn, "XADD", "xai1", "*", "foo", "bar")
        after = int(time.time() * 1000)
        # parse: $15\r\n1234567890123-0\r\n
        returned_id = resp.split("\r\n")[1]
        ms = int(returned_id.split("-")[0])
        seq = int(returned_id.split("-")[1])
        assert before <= ms <= after
        assert seq == 0

    def test_auto_id_type_is_stream(self, conn):
        send(conn, "XADD", "xai2", "*", "foo", "bar")
        assert send(conn, "TYPE", "xai2") == "+stream\r\n"


class TestXRange:
    def setup_stream(self, conn, key):
        send(conn, "XADD", key, "1-1", "foo", "bar")
        send(conn, "XADD", key, "2-1", "baz", "qux")
        send(conn, "XADD", key, "3-1", "a", "b")

    def test_xrange_full(self, conn):
        self.setup_stream(conn, "xr1")
        assert send(conn, "XRANGE", "xr1", "-", "+") == (
            "*3\r\n"
            "*2\r\n$3\r\n1-1\r\n*2\r\n$3\r\nfoo\r\n$3\r\nbar\r\n"
            "*2\r\n$3\r\n2-1\r\n*2\r\n$3\r\nbaz\r\n$3\r\nqux\r\n"
            "*2\r\n$3\r\n3-1\r\n*2\r\n$1\r\na\r\n$1\r\nb\r\n"
        )

    def test_xrange_dash_start(self, conn):
        self.setup_stream(conn, "xr2")
        assert send(conn, "XRANGE", "xr2", "-", "2-1") == (
            "*2\r\n"
            "*2\r\n$3\r\n1-1\r\n*2\r\n$3\r\nfoo\r\n$3\r\nbar\r\n"
            "*2\r\n$3\r\n2-1\r\n*2\r\n$3\r\nbaz\r\n$3\r\nqux\r\n"
        )

    def test_xrange_plus_end(self, conn):
        self.setup_stream(conn, "xr3")
        assert send(conn, "XRANGE", "xr3", "2-1", "+") == (
            "*2\r\n"
            "*2\r\n$3\r\n2-1\r\n*2\r\n$3\r\nbaz\r\n$3\r\nqux\r\n"
            "*2\r\n$3\r\n3-1\r\n*2\r\n$1\r\na\r\n$1\r\nb\r\n"
        )

    def test_xrange_exact(self, conn):
        self.setup_stream(conn, "xr4")
        assert send(conn, "XRANGE", "xr4", "1-1", "2-1") == (
            "*2\r\n"
            "*2\r\n$3\r\n1-1\r\n*2\r\n$3\r\nfoo\r\n$3\r\nbar\r\n"
            "*2\r\n$3\r\n2-1\r\n*2\r\n$3\r\nbaz\r\n$3\r\nqux\r\n"
        )

    def test_xrange_missing_key(self, conn):
        assert send(conn, "XRANGE", "nokey_xr", "-", "+") == "*0\r\n"

    def test_xrange_single_entry(self, conn):
        self.setup_stream(conn, "xr5")
        assert send(conn, "XRANGE", "xr5", "2-1", "2-1") == (
            "*1\r\n"
            "*2\r\n$3\r\n2-1\r\n*2\r\n$3\r\nbaz\r\n$3\r\nqux\r\n"
        )


class TestXRead:
    def test_xread_single_stream(self, conn):
        send(conn, "XADD", "xrd1", "1-1", "temp", "36")
        send(conn, "XADD", "xrd1", "2-1", "temp", "37")
        assert send(conn, "XREAD", "STREAMS", "xrd1", "1-0") == (
            "*1\r\n*2\r\n$4\r\nxrd1\r\n"
            "*2\r\n"
            "*2\r\n$3\r\n1-1\r\n*2\r\n$4\r\ntemp\r\n$2\r\n36\r\n"
            "*2\r\n$3\r\n2-1\r\n*2\r\n$4\r\ntemp\r\n$2\r\n37\r\n"
        )

    def test_xread_exclusive(self, conn):
        send(conn, "XADD", "xrd2", "1-1", "temp", "36")
        send(conn, "XADD", "xrd2", "2-1", "temp", "37")
        # should only return entry after 1-1
        assert send(conn, "XREAD", "STREAMS", "xrd2", "1-1") == (
            "*1\r\n*2\r\n$4\r\nxrd2\r\n"
            "*1\r\n"
            "*2\r\n$3\r\n2-1\r\n*2\r\n$4\r\ntemp\r\n$2\r\n37\r\n"
        )

    def test_xread_multiple_streams(self, conn):
        send(conn, "XADD", "xrd3a", "1-1", "temp", "36")
        send(conn, "XADD", "xrd3b", "1-1", "humid", "95")
        assert send(conn, "XREAD", "STREAMS", "xrd3a", "xrd3b", "0-0", "0-0") == (
            "*2\r\n"
            "*2\r\n$5\r\nxrd3a\r\n*1\r\n*2\r\n$3\r\n1-1\r\n*2\r\n$4\r\ntemp\r\n$2\r\n36\r\n"
            "*2\r\n$5\r\nxrd3b\r\n*1\r\n*2\r\n$3\r\n1-1\r\n*2\r\n$5\r\nhumid\r\n$2\r\n95\r\n"
        )

    def test_xread_no_new_entries(self, conn):
        send(conn, "XADD", "xrd4", "1-1", "foo", "bar")
        assert send(conn, "XREAD", "STREAMS", "xrd4", "1-1") == "*-1\r\n"


class TestXReadBlock:
    def test_xread_block_timeout(self, conn):
        assert send(conn, "XREAD", "BLOCK", "200", "STREAMS", "xbl1", "0-0") == "*-1\r\n"

    def test_xread_block_unblocked_by_xadd(self, conn, conn2):
        cmd = "*5\r\n$5\r\nXREAD\r\n$5\r\nBLOCK\r\n$4\r\n2000\r\n$7\r\nSTREAMS\r\n$5\r\nxbl2\r\n$3\r\n0-0\r\n"
        conn.sendall(cmd.encode())

        def xadd_later():
            time.sleep(0.3)
            s = new_conn()
            send(s, "XADD", "xbl2", "1-1", "foo", "bar")
            s.close()

        t = threading.Thread(target=xadd_later)
        t.start()
        t.join()
        time.sleep(0.2)

        assert conn.recv(4096).decode() == (
            "*1\r\n*2\r\n$5\r\nxbl2\r\n"
            "*1\r\n*2\r\n$3\r\n1-1\r\n*2\r\n$3\r\nfoo\r\n$3\r\nbar\r\n"
        )

    def test_xread_block_zero_indefinite(self, conn):
        cmd = "*5\r\n$5\r\nXREAD\r\n$5\r\nBLOCK\r\n$1\r\n0\r\n$7\r\nSTREAMS\r\n$5\r\nxbl3\r\n$3\r\n0-0\r\n"
        conn.sendall(cmd.encode())

        def xadd_later():
            time.sleep(0.3)
            s = new_conn()
            send(s, "XADD", "xbl3", "5-1", "hello", "world")
            s.close()

        t = threading.Thread(target=xadd_later)
        t.start()
        t.join()
        time.sleep(0.2)

        assert conn.recv(4096).decode() == (
            "*1\r\n*2\r\n$5\r\nxbl3\r\n"
            "*1\r\n*2\r\n$3\r\n5-1\r\n*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n"
        )

    def test_xread_block_dollar_only_new(self, conn):
        # add old entry first
        s = new_conn()
        send(s, "XADD", "xbl4", "1-1", "old", "data")
        s.close()

        # block with $
        cmd = "*5\r\n$5\r\nXREAD\r\n$5\r\nBLOCK\r\n$4\r\n2000\r\n$7\r\nSTREAMS\r\n$4\r\nxbl4\r\n$1\r\n$\r\n"
        conn.sendall(cmd.encode())

        def xadd_new():
            time.sleep(0.3)
            s = new_conn()
            send(s, "XADD", "xbl4", "2-1", "new", "data")
            s.close()

        t = threading.Thread(target=xadd_new)
        t.start()
        t.join()
        time.sleep(0.2)

        assert conn.recv(4096).decode() == (
            "*1\r\n*2\r\n$4\r\nxbl4\r\n"
            "*1\r\n*2\r\n$3\r\n2-1\r\n*2\r\n$3\r\nnew\r\n$4\r\ndata\r\n"
        )