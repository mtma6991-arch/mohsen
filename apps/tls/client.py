import json
import os
import socket


def socket_path() -> str:
    return os.environ.get("MOHSEN_TLS_SOCK", "/run/mohsen/tls.sock")


def notify(payload: dict, timeout: float = 2.0) -> dict:
    path = socket_path()
    data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.settimeout(timeout)
        client.connect(path)
        client.sendall(data)
        chunks = []
        while True:
            piece = client.recv(4096)
            if not piece:
                break
            chunks.append(piece)
            if b"\n" in piece:
                break
    finally:
        client.close()
    raw = b"".join(chunks).split(b"\n", 1)[0] or b"{}"
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "error": "پاسخ سرویس TLS نامعتبر بود."}
    if not isinstance(parsed, dict):
        return {"ok": False, "error": "پاسخ سرویس TLS نامعتبر بود."}
    return parsed
