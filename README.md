# ⚡ VoltDB

A lightweight, Redis-compatible in-memory database server built in Python. VoltDB speaks the Redis protocol (RESP2), meaning you can connect to it with any standard Redis client or the `redis-cli` tool.

---

## Requirements

- Python 3.11+
- No external dependencies

---

## Running the server

```bash
./your_program.sh
```

Or directly:

```bash
python3 app/main.py
```

The server starts on `localhost:6379` — the same default port as Redis.

---

## Usage

Connect with the standard Redis CLI:

```bash
redis-cli PING
# PONG

redis-cli ECHO "hello"
# hello

redis-cli SET foo bar
# OK

redis-cli GET foo
# bar

redis-cli SET foo bar PX 5000   # expires in 5000 milliseconds
redis-cli SET foo bar EX 10     # expires in 10 seconds

redis-cli GET foo   # returns nil after expiry
# (nil)
```

---

## Supported Commands

| Command | Syntax | Description |
|---|---|---|
| PING | `PING` | Returns PONG. Tests connectivity. |
| ECHO | `ECHO <message>` | Returns the message back to the client. |
| SET | `SET <key> <value> [EX seconds] [PX milliseconds]` | Sets a key with an optional expiry. |
| GET | `GET <key>` | Returns the value, or nil if missing or expired. |

---

## Running Tests

Make sure the server is running first, then in a separate terminal:

```bash
python3 tests/test_server.py
```

---

## Project Structure

```
voltdb/
├── app/
│   └── main.py        # all server logic
├── tests/
│   └── test_server.py # test suite
├── your_program.sh    # startup script
└── README.md
```

---

## License

MIT License. Use it however you like.
