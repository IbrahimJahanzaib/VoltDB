import asyncio

# key -> (value, expiry_ms or None)
store: dict = {}

# key -> [str]
list_store: dict = {}

# key -> [{"id": "ms-seq", "fields": [k, v, k, v, ...]}]
stream_store: dict = {}

# BLPOP waiters: key -> [(asyncio.Event, holder_dict)]
blpop_waiters: dict = {}

# XREAD BLOCK waiters: key -> [(asyncio.Event, holder_dict, after_id)]
xread_waiters: dict = {}