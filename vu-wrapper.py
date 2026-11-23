#!/usr/bin/env python3
"""Run the Venice Unleashed server and bridge console input to RCON.

AMP writes console commands to stdin, but VU only accepts commands over its
Frostbite remote administration protocol (RCON). This wrapper starts the
server, passes its output through unchanged, and sends every line typed into
the console to the local RCON port. The admin password is read from
Startup.txt, so it never appears on a command line.

Usage: vu-wrapper.py --rcon-port PORT --startup PATH -- <server command...>
"""

import argparse
import hashlib
import os
import shlex
import signal
import socket
import struct
import subprocess
import sys
import threading
import time


def log(msg):
    print(f"[RCON] {msg}", flush=True)


def encode_packet(seq, words):
    body = b""
    for w in words:
        data = w.encode("utf-8")
        body += struct.pack("<I", len(data)) + data + b"\0"
    # Bit 31 = 0: sent by client, bit 30 = 0: request.
    header = struct.pack("<III", seq & 0x3FFFFFFF, 12 + len(body), len(words))
    return header + body


def read_packet(sock):
    def recv_exact(n):
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("connection closed by server")
            buf += chunk
        return buf

    seq, size, count = struct.unpack("<III", recv_exact(12))
    body = recv_exact(size - 12)
    words, pos = [], 0
    for _ in range(count):
        (length,) = struct.unpack_from("<I", body, pos)
        pos += 4
        words.append(body[pos:pos + length].decode("utf-8", "replace"))
        pos += length + 1
    return seq, words


class Rcon:
    def __init__(self, port, startup_path):
        self.port = port
        self.startup_path = startup_path
        self.sock = None
        self.seq = 0

    def password(self):
        try:
            with open(self.startup_path, encoding="utf-8-sig") as f:
                for line in f:
                    parts = shlex.split(line, comments=False)
                    if len(parts) >= 2 and parts[0].lower() == "admin.password":
                        return parts[1]
        except (OSError, ValueError):
            pass
        return ""

    def request(self, words):
        self.seq += 1
        seq = self.seq
        self.sock.sendall(encode_packet(seq, words))
        while True:
            rseq, rwords = read_packet(self.sock)
            if rseq & 0x80000000:
                # Server-initiated event (only sent if events are enabled); ignore.
                continue
            if (rseq & 0x3FFFFFFF) == seq:
                return rwords

    def connect(self):
        pw = self.password()
        if not pw:
            raise RuntimeError("admin.password is empty in Startup.txt - set an RCON password in AMP")
        self.sock = socket.create_connection(("127.0.0.1", self.port), timeout=10)
        salt = self.request(["login.hashed"])
        if salt[:1] != ["OK"] or len(salt) < 2:
            raise RuntimeError(f"login.hashed failed: {' '.join(salt)}")
        digest = hashlib.md5(bytes.fromhex(salt[1]) + pw.encode("utf-8")).hexdigest().upper()
        resp = self.request(["login.hashed", digest])
        if resp[:1] != ["OK"]:
            raise RuntimeError(f"login failed: {' '.join(resp)}")

    def send(self, words):
        for attempt in (1, 2):
            try:
                if self.sock is None:
                    self.connect()
                return self.request(words)
            except (OSError, ConnectionError):
                self.close()
                if attempt == 2:
                    raise
        return []

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None


def console_loop(rcon):
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            words = shlex.split(line)
        except ValueError as e:
            log(f"could not parse command: {e}")
            continue
        try:
            resp = rcon.send(words)
            log(" ".join(shlex.quote(w) if (" " in w or not w) else w for w in resp))
        except Exception as e:  # keep the console alive whatever happens
            log(f"error: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rcon-port", type=int, required=True)
    ap.add_argument("--startup", required=True)
    ap.add_argument("command", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    cmd = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not cmd:
        ap.error("missing server command")

    child = subprocess.Popen(cmd, stdin=subprocess.DEVNULL)

    def stop(signum, _frame):
        log("stopping server...")
        try:
            child.terminate()
            child.wait(timeout=20)
        except subprocess.TimeoutExpired:
            child.kill()
        subprocess.run(["wineserver", "-k"], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sys.exit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    rcon = Rcon(args.rcon_port, args.startup)
    threading.Thread(target=console_loop, args=(rcon,), daemon=True).start()

    rc = child.wait()
    rcon.close()
    sys.exit(rc)


if __name__ == "__main__":
    main()
