import argparse
import json
import socket
import sys
from typing import Tuple


def print_payload(prefix: str, data: bytes, addr: Tuple[str, int] | None = None) -> None:
    try:
        text = data.decode("utf-8", errors="replace")
    except Exception:
        text = repr(data)
    where = f" from {addr[0]}:{addr[1]}" if addr else ""
    print(f"[RECV]{where} {len(data)} bytes: {text}")
    # Try to pretty-print JSON if applicable
    try:
        obj = json.loads(text)
        print("        as JSON:", json.dumps(obj, ensure_ascii=False))
    except Exception:
        pass


def run_udp(host: str, port: int) -> None:
    print(f"[UDP] Listening on {host}:{port} ... Ctrl+C to stop")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host, port))
        while True:
            data, addr = s.recvfrom(4096)
            print_payload("UDP", data, addr)


def run_tcp(host: str, port: int) -> None:
    print(f"[TCP] Listening on {host}:{port} ... Ctrl+C to stop")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        # Reuse address for quick restarts
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(5)
        while True:
            conn, addr = srv.accept()
            with conn:
                # Read until client closes the connection
                chunks: list[bytes] = []
                while True:
                    buf = conn.recv(4096)
                    if not buf:
                        break
                    chunks.append(buf)
                data = b"".join(chunks)
                print_payload("TCP", data, addr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Receive and print RobotClient messages (TCP/UDP)")
    parser.add_argument("--transport", choices=["tcp", "udp"], default="tcp", help="Protocol to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=5555, help="Port to bind")
    args = parser.parse_args()

    try:
        if args.transport == "udp":
            run_udp(args.host, args.port)
        else:
            run_tcp(args.host, args.port)
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()

