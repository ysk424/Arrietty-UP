#!/usr/bin/env python3
"""Send one null-delimited execute request to a Blender MCP bridge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import sys


def execute(code: str, port: int, timeout: float = 30.0) -> dict:
    request = {"type": "execute", "strict_json": True, "code": code}
    with socket.create_connection(("127.0.0.1", port), timeout) as connection:
        connection.settimeout(timeout)
        connection.sendall(json.dumps(request).encode("utf-8") + b"\0")
        chunks: list[bytes] = []
        while True:
            chunk = connection.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\0" in chunk:
                break
    payload = b"".join(chunks).split(b"\0", 1)[0]
    if not payload:
        raise RuntimeError("Blender MCP returned no response")
    return json.loads(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--code")
    source.add_argument("--file", type=Path)
    parser.add_argument("--port", type=int, default=9877)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    code = args.code if args.code is not None else args.file.read_text(encoding="utf-8")
    response = execute(code, args.port, args.timeout)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if response.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
