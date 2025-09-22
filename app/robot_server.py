import json
import socket
import threading
from dataclasses import dataclass, field
from typing import Optional

from .events import EventBus


@dataclass
class RobotEventServer:
    host: str
    port: int
    transport: str  # "tcp" or "udp"
    bus: EventBus

    _t: Optional[threading.Thread] = field(default=None, init=False)
    _stop: threading.Event = field(default_factory=threading.Event, init=False)

    def start(self) -> None:
        if self._t and self._t.is_alive():
            return
        self._stop.clear()
        if self.transport.lower() == "udp":
            self._t = threading.Thread(target=self._run_udp, daemon=True)
        else:
            self._t = threading.Thread(target=self._run_tcp, daemon=True)
        self._t.start()
        print(f"[ROBOT][srv] start {self.transport.upper()} {self.host}:{self.port}")

    def stop(self) -> None:
        if not self._t:
            return
        self._stop.set()
        # For UDP we rely on socket timeout; for TCP accept loop timeout
        self._t.join(timeout=2.0)
        print("[ROBOT][srv] stopped")

    def _run_udp(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.settimeout(1.0)
            s.bind((self.host, self.port))
            while not self._stop.is_set():
                try:
                    data, addr = s.recvfrom(65535)
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[ROBOT][srv][udp][err] {e}")
                    continue
                try:
                    text = data.decode("utf-8", errors="replace").strip()
                    obj = json.loads(text)
                except Exception:
                    obj = {"kind": "robot_event", "text": text}
                obj.setdefault("kind", "robot_event")
                obj.setdefault("source", f"udp://{addr[0]}:{addr[1]}")
                self.bus.publish(obj)
                print(f"[ROBOT][srv][udp] from {addr}: {obj}")
        finally:
            s.close()

    def _run_tcp(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.settimeout(1.0)
            srv.bind((self.host, self.port))
            srv.listen(5)
            while not self._stop.is_set():
                try:
                    conn, addr = srv.accept()
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[ROBOT][srv][tcp][accept][err] {e}")
                    continue
                threading.Thread(target=self._handle_tcp_conn, args=(conn, addr), daemon=True).start()
        finally:
            srv.close()

    def _handle_tcp_conn(self, conn: socket.socket, addr) -> None:
        with conn:
            try:
                conn.settimeout(2.0)
                buf = b""
                while True:
                    try:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        buf += chunk
                        # Try to split by newlines (JSON lines)
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            self._publish_tcp_line(line, addr)
                    except socket.timeout:
                        # publish any remaining buffer as a single message
                        if buf:
                            self._publish_tcp_line(buf, addr)
                            buf = b""
                        break
                # leftover
                if buf:
                    self._publish_tcp_line(buf, addr)
            except Exception as e:
                print(f"[ROBOT][srv][tcp][conn][err] {e}")

    def _publish_tcp_line(self, data: bytes, addr) -> None:
        text = data.decode("utf-8", errors="replace").strip()
        if not text:
            return
        try:
            obj = json.loads(text)
        except Exception:
            obj = {"kind": "robot_event", "text": text}
        obj.setdefault("kind", "robot_event")
        obj.setdefault("source", f"tcp://{addr[0]}:{addr[1]}")
        self.bus.publish(obj)
        print(f"[ROBOT][srv][tcp] from {addr}: {obj}")

