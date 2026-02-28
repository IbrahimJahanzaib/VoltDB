def parse_resp(data: bytes) -> list[str]:
    """Parse raw RESP bytes into a list of strings e.g. ['SET', 'foo', 'bar']"""
    lines = data.split(b"\r\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(b"*"):
            i += 1
        elif line.startswith(b"$"):
            i += 1
            if i < len(lines):
                result.append(lines[i].decode("utf-8"))
            i += 1
        else:
            i += 1
    return result