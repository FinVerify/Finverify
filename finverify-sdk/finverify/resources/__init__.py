"""
finverify.resources — Request/response specs, shared by sync + async clients
===============================================================================
Each module here holds pure functions: build a (method, path, params, body)
tuple for a call, and parse the raw JSON response into a typed model.
Neither ``client.py`` nor ``async_client.py`` duplicates this logic — they
only differ in *how* they execute the transport call (blocking vs ``await``).
"""
