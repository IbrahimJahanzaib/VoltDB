def simple_string(s: str) -> bytes:
    return f"+{s}\r\n".encode()

def error(msg: str) -> bytes:
    return f"-{msg}\r\n".encode()

def integer(n: int) -> bytes:
    return f":{n}\r\n".encode()

def bulk_string(s: str) -> bytes:
    return f"${len(s)}\r\n{s}\r\n".encode()

def null_bulk_string() -> bytes:
    return b"$-1\r\n"

def null_array() -> bytes:
    return b"*-1\r\n"

def empty_array() -> bytes:
    return b"*0\r\n"

def array(items: list[str]) -> bytes:
    resp = f"*{len(items)}\r\n"
    for item in items:
        resp += f"${len(item)}\r\n{item}\r\n"
    return resp.encode()

def encode_stream_entries(entries: list[dict]) -> str:
    """Encode stream entries as a RESP array string (not bytes, for composing)"""
    resp = f"*{len(entries)}\r\n"
    for entry in entries:
        fields = entry["fields"]
        resp += f"*2\r\n"
        resp += f"${len(entry['id'])}\r\n{entry['id']}\r\n"
        resp += f"*{len(fields)}\r\n"
        for f in fields:
            resp += f"${len(f)}\r\n{f}\r\n"
    return resp