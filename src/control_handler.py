# Original Source: https://github.com/jtauber/applepy
from __future__ import annotations

import http.server
import json
import re
import select
from typing import Any, TYPE_CHECKING, Callable

from disassemble import Disassemble

if TYPE_CHECKING:
    import socket
    from runtime import Runtime


class ControlHandler(http.server.BaseHTTPRequestHandler):

    def __init__(
        self, request: socket.socket, client_address: tuple[str, int], server: http.server.HTTPServer, runtime: Runtime
    ) -> None:
        self.runtime = runtime
        self.disassemble = Disassemble(self.runtime)

        self.get_urls: dict[str, Callable[[re.Match[str]], None]] = {
            r"/disassemble/(\d+)$": self.get_disassemble,
            r"/memory/(\d+)(-(\d+))?$": self.get_memory,
            r"/memory/(\d+)(-(\d+))?/raw$": self.get_memory_raw,
            r"/status$": self.get_status,
        }

        self.post_urls: dict[str, Callable[[re.Match[str]], None]] = {
            r"/memory/(\d+)(-(\d+))?$": self.post_memory,
            r"/memory/(\d+)(-(\d+))?/raw$": self.post_memory_raw,
            r"/reset$": self.post_reset,
        }

        http.server.BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def log_request(self, code: int | str = "-", size: int | str = 0) -> None:
        pass

    def dispatch(self, urls: dict[str, Callable[[re.Match[str]], None]]) -> None:
        for r, f in list(urls.items()):
            m = re.match(r, self.path)
            if m is not None:
                f(m)
                break
        else:
            self.send_response(404)
            self.end_headers()

    def response(self, s: str) -> None:
        self.send_response(200)
        self.send_header("Content-Length", str(len(s)))
        self.end_headers()
        self.wfile.write(s.encode())

    def do_GET(self) -> None:
        self.dispatch(self.get_urls)

    def do_POST(self) -> None:
        self.dispatch(self.post_urls)

    def get_disassemble(self, m: re.Match[str]) -> None:
        addr = int(m.group(1))
        r: list[dict[str, Any]] = []
        n = 20
        while n > 0:
            dis, length = self.disassemble.disasm(addr)
            r.append(dis)
            addr += length
            n -= 1
        self.response(json.dumps(r))

    def get_memory_raw(self, m: re.Match[str]) -> None:
        addr = int(m.group(1))
        e = m.group(3)
        if e is not None:
            end = int(e)
        else:
            end = addr
        self.response("".join([chr(self.runtime.read_byte(x)) for x in range(addr, end + 1)]))

    def get_memory(self, m: re.Match[str]) -> None:
        addr = int(m.group(1))
        e = m.group(3)
        if e is not None:
            end = int(e)
        else:
            end = addr
        self.response(json.dumps(list(map(self.runtime.read_byte, list(range(addr, end + 1))))))

    def get_status(self, m: re.Match[str]) -> None:
        self.response(json.dumps(self.runtime.get_status()))

    def post_memory(self, m: re.Match[str]) -> None:
        addr = int(m.group(1))
        e = m.group(3)
        if e is not None:
            end = int(e)
        else:
            end = addr
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        for i, a in enumerate(range(addr, end + 1)):
            self.runtime.write_byte(a, data[i])
        self.response("")

    def post_memory_raw(self, m: re.Match[str]) -> None:
        addr = int(m.group(1))
        e = m.group(3)
        if e is not None:
            end = int(e)
        else:
            end = addr
        data = self.rfile.read(int(self.headers["Content-Length"]))
        for i, a in enumerate(range(addr, end + 1)):
            self.runtime.write_byte(a, data[i])
        self.response("")

    def post_reset(self, m: re.Match[str]) -> None:
        self.runtime.reset()
        self.response("")


class ControlHandlerFactory:

    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime

    def __call__(
        self, request: socket.socket, client_address: tuple[str, int], server: http.server.HTTPServer
    ) -> ControlHandler:
        return ControlHandler(request, client_address, server, self.runtime)


class ControlServer(http.server.HTTPServer):

    def __init__(self, pair: tuple[str, int], handler: ControlHandlerFactory) -> None:
        http.server.HTTPServer.__init__(self, pair, handler)

    def handle(self, timeout: float) -> None:
        sockets = [self]
        rs, _, _ = select.select(sockets, [], [], timeout)
        for s in rs:
            if s is self:
                self._handle_request_noblock()  # type: ignore[attr-defined]
            else:
                pass


def create_controller(runtime: Runtime, port: int) -> ControlServer:
    return ControlServer(("127.0.0.1", port), ControlHandlerFactory(runtime))
