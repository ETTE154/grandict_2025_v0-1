import json
import socket
from dataclasses import dataclass


@dataclass
class RobotClient:
    host: str
    port: int
    transport: str = "udp"  # "tcp" or "udp"

    def send(self, name: str, value: int = 1) -> None:
        payload_dict = {"name": name, "value": value}
        payload = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
        print(f"[ROBOT][send] {self.transport.upper()} {self.host}:{self.port} -> {payload_dict}")
        if self.transport.lower() == "udp":
            self._send_udp(payload)
        else:
            self._send_tcp(payload)

    def _send_tcp(self, data: bytes) -> None:
        with socket.create_connection((self.host, self.port), timeout=3) as s:
            s.sendall(data)

    def _send_udp(self, data: bytes) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(data, (self.host, self.port))
