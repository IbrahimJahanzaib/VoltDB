import time
from app import store, encoder


def handle_set(parts: list[str]) -> bytes:
    if len(parts) < 3:
        return encoder.error("ERR wrong number of arguments for SET")
    key, value = parts[1], parts[2]
    expiry = None
    if len(parts) >= 5:
        option = parts[3].upper()
        if option == "PX":
            expiry = time.time() * 1000 + int(parts[4])
        elif option == "EX":
            expiry = time.time() * 1000 + int(parts[4]) * 1000
    store.store[key] = (value, expiry)
    return encoder.simple_string("OK")


def handle_get(parts: list[str]) -> bytes:
    if len(parts) < 2:
        return encoder.error("ERR wrong number of arguments for GET")
    key = parts[1]
    if key not in store.store:
        return encoder.null_bulk_string()
    value, expiry = store.store[key]
    if expiry is not None and time.time() * 1000 > expiry:
        del store.store[key]
        return encoder.null_bulk_string()
    return encoder.bulk_string(value)


def handle_type(parts: list[str]) -> bytes:
    if len(parts) < 2:
        return encoder.error("ERR wrong number of arguments for TYPE")
    key = parts[1]
    if key in store.store:
        return encoder.simple_string("string")
    if key in store.list_store:
        return encoder.simple_string("list")
    if key in store.stream_store:
        return encoder.simple_string("stream")
    return encoder.simple_string("none")


def handle_incr(parts: list[str]) -> bytes:
    if len(parts) < 2:
        return encoder.error("ERR wrong number of arguments for INCR")
    key = parts[1]

    if key not in store.store:
        store.store[key] = ("1", None)
        return encoder.integer(1)

    value, expiry = store.store[key]
    try:
        new_value = int(value) + 1
    except ValueError:
        return encoder.error("ERR value is not an integer or out of range")

    store.store[key] = (str(new_value), expiry)
    return encoder.integer(new_value)