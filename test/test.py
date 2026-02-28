import socket
import time
import sys
import threading

HOST = "localhost"
PORT = 6379

def send_command(sock, *args):
    cmd = f"*{len(args)}\r\n"
    for arg in args:
        cmd += f"${len(arg)}\r\n{arg}\r\n"
    sock.sendall(cmd.encode())
    return sock.recv(4096).decode()

def new_connection():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.settimeout(5)
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
    test("PING returns PONG",  send_command(s, "PING"),  "+PONG\r\n")
    test("ping lowercase",     send_command(s, "ping"),  "+PONG\r\n")
    test("multiple PINGs",     send_command(s, "PING"),  "+PONG\r\n")
    s.close()

def test_echo():
    print("\n📦 ECHO")
    s = new_connection()
    test("ECHO hey",         send_command(s, "ECHO", "hey"),     "$3\r\nhey\r\n")
    test("ECHO hello",       send_command(s, "ECHO", "hello"),   "$5\r\nhello\r\n")
    test("ECHO empty",       send_command(s, "ECHO", ""),        "$0\r\n\r\n")
    test("echo lowercase",   send_command(s, "echo", "test"),    "$4\r\ntest\r\n")
    test("ECHO long string",
         send_command(s, "ECHO", "a" * 100),
         f"$100\r\n{'a' * 100}\r\n")
    s.close()

def test_set_get():
    print("\n📦 SET / GET")
    s = new_connection()
    test("SET foo bar returns OK",  send_command(s, "SET", "foo", "bar"),    "+OK\r\n")
    test("GET foo returns bar",     send_command(s, "GET", "foo"),           "$3\r\nbar\r\n")
    test("SET overwrite",           send_command(s, "SET", "foo", "baz"),    "+OK\r\n")
    test("GET after overwrite",     send_command(s, "GET", "foo"),           "$3\r\nbaz\r\n")
    test("GET missing key",         send_command(s, "GET", "nonexistent"),   "$-1\r\n")
    test("SET numeric value",       send_command(s, "SET", "num", "42"),     "+OK\r\n")
    test("GET numeric value",       send_command(s, "GET", "num"),           "$2\r\n42\r\n")
    test("SET empty value",         send_command(s, "SET", "empty", ""),     "+OK\r\n")
    test("GET empty value",         send_command(s, "GET", "empty"),         "$0\r\n\r\n")
    s.close()

def test_expiry_px():
    print("\n📦 SET with PX expiry")
    s = new_connection()
    send_command(s, "SET", "ex1", "val", "PX", "300")
    test("GET before PX expiry",    send_command(s, "GET", "ex1"),  "$3\r\nval\r\n")
    time.sleep(0.4)
    test("GET after PX expiry",     send_command(s, "GET", "ex1"),  "$-1\r\n")
    send_command(s, "SET", "ex2", "hello", "PX", "100")
    test("GET before short expiry", send_command(s, "GET", "ex2"),  "$5\r\nhello\r\n")
    time.sleep(0.2)
    test("GET after short expiry",  send_command(s, "GET", "ex2"),  "$-1\r\n")
    s.close()

def test_expiry_ex():
    print("\n📦 SET with EX expiry")
    s = new_connection()
    send_command(s, "SET", "exs", "world", "EX", "1")
    test("GET before EX expiry",  send_command(s, "GET", "exs"),  "$5\r\nworld\r\n")
    time.sleep(1.1)
    test("GET after EX expiry",   send_command(s, "GET", "exs"),  "$-1\r\n")
    s.close()

def test_concurrent_clients():
    print("\n📦 Concurrent clients")
    s1 = new_connection()
    s2 = new_connection()
    send_command(s1, "SET", "shared", "from_s1")
    test("client 2 sees client 1's write", send_command(s2, "GET", "shared"), "$7\r\nfrom_s1\r\n")
    send_command(s2, "SET", "shared", "from_s2")
    test("client 1 sees client 2's write", send_command(s1, "GET", "shared"), "$7\r\nfrom_s2\r\n")
    test("client 1 PING", send_command(s1, "PING"), "+PONG\r\n")
    test("client 2 PING", send_command(s2, "PING"), "+PONG\r\n")
    s1.close()
    s2.close()

def test_case_insensitive():
    print("\n📦 Case insensitivity")
    s = new_connection()
    test("PING uppercase",  send_command(s, "PING"),        "+PONG\r\n")
    test("ping lowercase",  send_command(s, "ping"),        "+PONG\r\n")
    test("Ping mixed",      send_command(s, "Ping"),        "+PONG\r\n")
    test("ECHO uppercase",  send_command(s, "ECHO", "hi"),  "$2\r\nhi\r\n")
    test("echo lowercase",  send_command(s, "echo", "hi"),  "$2\r\nhi\r\n")
    test("EcHo mixed",      send_command(s, "EcHo", "hi"),  "$2\r\nhi\r\n")
    s.close()

def test_rpush():
    print("\n📦 RPUSH")
    s = new_connection()
    test("RPUSH new list",           send_command(s, "RPUSH", "mylist", "a"),             ":1\r\n")
    test("RPUSH append one",         send_command(s, "RPUSH", "mylist", "b"),             ":2\r\n")
    test("RPUSH append another",     send_command(s, "RPUSH", "mylist", "c"),             ":3\r\n")
    test("RPUSH multiple elements",  send_command(s, "RPUSH", "mylist", "d", "e", "f"),  ":6\r\n")
    test("RPUSH new list multi",     send_command(s, "RPUSH", "newlist", "x", "y", "z"), ":3\r\n")
    test("rpush lowercase",          send_command(s, "rpush", "lclist", "val"),           ":1\r\n")
    s.close()

def test_lrange():
    print("\n📦 LRANGE")
    s = new_connection()
    send_command(s, "RPUSH", "rangelist", "a", "b", "c", "d", "e")
    test("LRANGE full",
         send_command(s, "LRANGE", "rangelist", "0", "4"),
         "*5\r\n$1\r\na\r\n$1\r\nb\r\n$1\r\nc\r\n$1\r\nd\r\n$1\r\ne\r\n")
    test("LRANGE first two",
         send_command(s, "LRANGE", "rangelist", "0", "1"),
         "*2\r\n$1\r\na\r\n$1\r\nb\r\n")
    test("LRANGE middle",
         send_command(s, "LRANGE", "rangelist", "2", "4"),
         "*3\r\n$1\r\nc\r\n$1\r\nd\r\n$1\r\ne\r\n")
    test("LRANGE single element",
         send_command(s, "LRANGE", "rangelist", "2", "2"),
         "*1\r\n$1\r\nc\r\n")
    test("LRANGE stop out of bounds",
         send_command(s, "LRANGE", "rangelist", "0", "100"),
         "*5\r\n$1\r\na\r\n$1\r\nb\r\n$1\r\nc\r\n$1\r\nd\r\n$1\r\ne\r\n")
    test("LRANGE start out of bounds",
         send_command(s, "LRANGE", "rangelist", "10", "20"),
         "*0\r\n")
    test("LRANGE start greater than stop",
         send_command(s, "LRANGE", "rangelist", "3", "1"),
         "*0\r\n")
    test("LRANGE missing key",
         send_command(s, "LRANGE", "nokey", "0", "5"),
         "*0\r\n")
    test("LRANGE negative stop -1",
         send_command(s, "LRANGE", "rangelist", "0", "-1"),
         "*5\r\n$1\r\na\r\n$1\r\nb\r\n$1\r\nc\r\n$1\r\nd\r\n$1\r\ne\r\n")
    test("LRANGE negative stop -2",
         send_command(s, "LRANGE", "rangelist", "0", "-2"),
         "*4\r\n$1\r\na\r\n$1\r\nb\r\n$1\r\nc\r\n$1\r\nd\r\n")
    test("lrange lowercase",
         send_command(s, "lrange", "rangelist", "0", "0"),
         "*1\r\n$1\r\na\r\n")
    s.close()

def test_llen():
    print("\n📦 LLEN")
    s = new_connection()
    send_command(s, "RPUSH", "lenlist", "a", "b", "c", "d")
    test("LLEN existing list",        send_command(s, "LLEN", "lenlist"),   ":4\r\n")
    send_command(s, "RPUSH", "lenlist", "e")
    test("LLEN after append",         send_command(s, "LLEN", "lenlist"),   ":5\r\n")
    test("LLEN missing key",          send_command(s, "LLEN", "nokey"),     ":0\r\n")
    test("llen lowercase",            send_command(s, "llen", "lenlist"),   ":5\r\n")
    send_command(s, "RPUSH", "single", "only")
    test("LLEN single element list",  send_command(s, "LLEN", "single"),    ":1\r\n")
    s.close()

def test_lpop():
    print("\n📦 LPOP")
    s = new_connection()
    send_command(s, "RPUSH", "poplist", "one", "two", "three", "four", "five")
    test("LPOP first element",     send_command(s, "LPOP", "poplist"),       "$3\r\none\r\n")
    test("LPOP second element",    send_command(s, "LPOP", "poplist"),       "$3\r\ntwo\r\n")
    test("LPOP third element",     send_command(s, "LPOP", "poplist"),       "$5\r\nthree\r\n")
    test("LRANGE after 3 LPOPs",
         send_command(s, "LRANGE", "poplist", "0", "-1"),
         "*2\r\n$4\r\nfour\r\n$4\r\nfive\r\n")
    test("LLEN after 3 LPOPs",    send_command(s, "LLEN", "poplist"),       ":2\r\n")
    test("LPOP missing key",       send_command(s, "LPOP", "nokey"),        "$-1\r\n")
    test("lpop lowercase",         send_command(s, "lpop", "poplist"),      "$4\r\nfour\r\n")
    send_command(s, "LPOP", "poplist")
    test("LPOP empty list",        send_command(s, "LPOP", "poplist"),      "$-1\r\n")
    s.close()

def test_lpop_multi():
    print("\n📦 LPOP with count")
    s = new_connection()
    send_command(s, "RPUSH", "mlist", "one", "two", "three", "four", "five")
    test("LPOP 2 elements",
         send_command(s, "LPOP", "mlist", "2"),
         "*2\r\n$3\r\none\r\n$3\r\ntwo\r\n")
    test("LRANGE after LPOP 2",
         send_command(s, "LRANGE", "mlist", "0", "-1"),
         "*3\r\n$5\r\nthree\r\n$4\r\nfour\r\n$4\r\nfive\r\n")
    test("LPOP count exceeds length",
         send_command(s, "LPOP", "mlist", "100"),
         "*3\r\n$5\r\nthree\r\n$4\r\nfour\r\n$4\r\nfive\r\n")
    test("LRANGE after full pop",
         send_command(s, "LRANGE", "mlist", "0", "-1"),
         "*0\r\n")
    s.close()

def test_blpop():
    print("\n📦 BLPOP")
    s = new_connection()

    # element already available
    send_command(s, "RPUSH", "blist", "hello")
    test("BLPOP element available",
         send_command(s, "BLPOP", "blist", "1"),
         "*2\r\n$5\r\nblist\r\n$5\r\nhello\r\n")

    # timeout — no element added
    s2 = new_connection()
    s2.settimeout(3)
    start = time.time()
    test("BLPOP timeout returns null array",
         send_command(s2, "BLPOP", "emptylist", "0.2"),
         "*-1\r\n")
    elapsed = time.time() - start
    assert 0.1 < elapsed < 1.0, f"BLPOP timeout took unexpected time: {elapsed:.2f}s"
    print(f"  ✅ PASS: BLPOP timeout duration (~{elapsed:.2f}s)")
    s2.close()

    # element pushed while blocked
    s3 = new_connection()
    s3.settimeout(3)
    result = []

    def blocking_client():
        result.append(s3.recv(4096).decode())

    # send BLPOP first (blocks)
    cmd = "*3\r\n$6\r\nBLPOP\r\n$9\r\nwaitlist1\r\n$1\r\n2\r\n"
    s3.sendall(cmd.encode())

    # push from another connection after short delay
    def push_later():
        time.sleep(0.2)
        sp = new_connection()
        send_command(sp, "RPUSH", "waitlist1", "world")
        sp.close()

    t = threading.Thread(target=push_later)
    t.start()
    t.join()
    time.sleep(0.1)

    test("BLPOP unblocked by RPUSH",
         s3.recv(4096).decode(),
         "*2\r\n$9\r\nwaitlist1\r\n$5\r\nworld\r\n")
    s3.close()
    s.close()

def test_type():
    print("\n📦 TYPE")
    s = new_connection()
    send_command(s, "SET", "strkey", "hello")
    test("TYPE string key",   send_command(s, "TYPE", "strkey"),   "+string\r\n")
    send_command(s, "RPUSH", "listkey", "a", "b")
    test("TYPE list key",     send_command(s, "TYPE", "listkey"),  "+list\r\n")
    test("TYPE missing key",  send_command(s, "TYPE", "nokey"),    "+none\r\n")
    send_command(s, "XADD", "streamkey", "1-1", "foo", "bar")
    test("TYPE stream key",   send_command(s, "TYPE", "streamkey"), "+stream\r\n")
    s.close()

def test_xadd():
    print("\n📦 XADD")
    s = new_connection()

    # basic add
    test("XADD returns entry id",
         send_command(s, "XADD", "mystream", "1-1", "foo", "bar"),
         "$3\r\n1-1\r\n")

    # add second entry
    test("XADD second entry",
         send_command(s, "XADD", "mystream", "2-1", "baz", "qux"),
         "$3\r\n2-1\r\n")

    # invalid: same id
    test("XADD duplicate id",
         send_command(s, "XADD", "mystream", "2-1", "a", "b"),
         "-ERR The ID specified in XADD is equal or smaller than the target stream top item\r\n")

    # invalid: smaller ms
    test("XADD smaller ms",
         send_command(s, "XADD", "mystream", "1-5", "a", "b"),
         "-ERR The ID specified in XADD is equal or smaller than the target stream top item\r\n")

    # invalid: 0-0
    test("XADD 0-0 id",
         send_command(s, "XADD", "mystream", "0-0", "a", "b"),
         "-ERR The ID specified in XADD must be greater than 0-0\r\n")

    # valid minimum id on new stream
    test("XADD minimum valid id",
         send_command(s, "XADD", "freshstream", "0-1", "x", "y"),
         "$3\r\n0-1\r\n")

    # type check
    test("TYPE after XADD",
         send_command(s, "TYPE", "mystream"),
         "+stream\r\n")

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
    test_rpush()
    test_lrange()
    test_llen()
    test_lpop()
    test_lpop_multi()
    test_blpop()
    test_type()
    test_xadd()

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print("💥 Some tests failed.")
    sys.exit(0 if failed == 0 else 1)