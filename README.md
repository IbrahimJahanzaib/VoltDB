# ⚡ VoltDB

A lightweight, Redis-compatible in-memory database server built in Python. VoltDB speaks the Redis protocol (RESP2), meaning you can connect to it with any standard Redis client or the `redis-cli` tool.

---

## Requirements

- Python 3.11+
- No external dependencies for the server
- `pytest` for running tests

---

## Running the server

```bash
./your_program.sh
```

Or directly:

```bash
python3 -m app.main
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

redis-cli INCR counter
# (integer) 1

redis-cli RPUSH mylist a b c
# (integer) 3

redis-cli LRANGE mylist 0 -1
# 1) "a"
# 2) "b"
# 3) "c"

redis-cli XADD stream * temperature 36
# "1234567890123-0"

redis-cli XRANGE stream - +
# 1) 1) "1234567890123-0"
#    2) 1) "temperature"
#       2) "36"
```

---

## Supported Commands

### Strings
| Command | Syntax | Description |
|---|---|---|
| PING | `PING` | Returns PONG. Tests connectivity. |
| ECHO | `ECHO <message>` | Returns the message back. |
| SET | `SET <key> <value> [EX seconds] [PX milliseconds]` | Sets a key with optional expiry. |
| GET | `GET <key>` | Returns the value, or nil if missing or expired. |
| INCR | `INCR <key>` | Increments a key by 1. Creates it at 1 if missing. |
| TYPE | `TYPE <key>` | Returns the type of a key: string, list, stream, or none. |

### Lists
| Command | Syntax | Description |
|---|---|---|
| RPUSH | `RPUSH <key> <element> [element ...]` | Appends elements to a list. Creates it if needed. |
| LRANGE | `LRANGE <key> <start> <stop>` | Returns elements in range. Supports negative indexes. |
| LLEN | `LLEN <key>` | Returns the length of a list. |
| LPOP | `LPOP <key> [count]` | Removes and returns elements from the front. |
| BLPOP | `BLPOP <key> <timeout>` | Blocking LPOP. Waits until an element is available. |

### Streams
| Command | Syntax | Description |
|---|---|---|
| XADD | `XADD <key> <id> <field> <value> [...]` | Appends an entry to a stream. ID can be explicit, `ms-*`, or `*`. |
| XRANGE | `XRANGE <key> <start> <end>` | Returns entries in range. Supports `-` and `+`. |
| XREAD | `XREAD [BLOCK ms] STREAMS <key> [key ...] <id> [id ...]` | Reads from one or more streams. Supports blocking. |

### Transactions
| Command | Syntax | Description |
|---|---|---|
| MULTI | `MULTI` | Starts a transaction. Commands are queued. |
| EXEC | `EXEC` | Executes all queued commands and returns their responses. |
| DISCARD | `DISCARD` | Discards the queued commands and exits the transaction. |

---

## Transactions

VoltDB supports atomic transactions via `MULTI`/`EXEC`:

```bash
redis-cli
> MULTI
OK
> SET foo 41
QUEUED
> INCR foo
QUEUED
> EXEC
1) OK
2) (integer) 42
```

---

## Project Structure

```
voltdb/
├── app/
│   ├── main.py          # entry point
│   ├── server.py        # connection handling and command routing
│   ├── parser.py        # RESP2 parser
│   ├── encoder.py       # RESP2 encoder helpers
│   ├── store.py         # in-memory state
│   └── commands/
│       ├── strings.py   # SET, GET, INCR, TYPE
│       ├── lists.py     # RPUSH, LRANGE, LLEN, LPOP, BLPOP
│       └── streams.py   # XADD, XRANGE, XREAD
├── tests/
│   ├── conftest.py      # shared fixtures
│   ├── test_strings.py
│   ├── test_lists.py
│   └── test_streams.py
├── your_program.sh
└── README.md
```

---

## Running Tests

Make sure the server is running first, then in a separate terminal:

```bash
pytest -v
```

---

## License

MIT License. Use it however you like.