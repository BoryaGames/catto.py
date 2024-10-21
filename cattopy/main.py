import re
import os
import json
import mimetypes
import asyncio
import socket
import uvicorn
import urllib.parse
from collections.abc import Callable, Awaitable
from typing import Any
from uvicorn._types import HTTPScope, ASGIReceiveCallable, ASGISendCallable


class _PatchedUvServer(uvicorn.Server):
    def __init__(self, config: uvicorn.Config):
        super().__init__(config)
        self.cpyServer: Server | None = None

    async def startup(self, sockets: list[socket.socket] | None = None):
        await super().startup(sockets)
        if self.cpyServer and self.cpyServer.onRunning:
            await self.cpyServer.onRunning()


class Server:
    def __init__(self, port: str | int | None = None, debug: bool = False):
        self.port = ""
        if port:
            self.port = str(port)
        elif os.getenv("PORT"):
            self.port = os.getenv("PORT")
        if not self.port and os.getenv("SERVER_PORT"):
            self.port = os.getenv("SERVER_PORT")
        if not self.port:
            self.port = "80"
        self.port = int(self.port)
        self.debug = debug
        self.config = uvicorn.Config(
            self._makehandler(),
            host="0.0.0.0",
            port=self.port,
            log_level="trace" if self.debug else "error",
            headers=[("server", "catto.py")],
        )
        self.server = _PatchedUvServer(self.config)
        self.server.cpyServer = self
        self.onRunning: Callable[[], Awaitable[Any]] | None = None
        self.middlewares: list[Middleware] = []

    def _maketemplate(self, path: str) -> str:
        return (
            "^"
            + re.sub(
                r"/{([a-zA-Z0-9_]+)}",
                "/(?P<\\g<1>>[a-zA-Z0-9_]+)",
                path.replace("*", ".*"),
                0,
            )
            + "$"
        )

    async def _run(self):
        await self.server.serve()

    def _makehandler(self):
        async def _fakehandler(
            scope: HTTPScope, receive: ASGIReceiveCallable, send: ASGISendCallable
        ):
            await self._handler(scope, receive, send)

        return _fakehandler

    async def _handler(
        self, scope: HTTPScope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ):
        if scope["type"] != "http":
            return
        for middleware in self.middlewares:
            if middleware.method != "*" and middleware.method != scope["method"]:
                continue
            pathMatch = re.search(middleware.path, scope["path"])
            if not pathMatch:
                continue
            request = Request(self, scope, receive, pathMatch.groupdict())
            result = await middleware.handler(request)
            if isinstance(result, Response):
                headers: list[tuple[bytes, bytes]] = []
                for name, value in result.headers.items():
                    headers.append((name.encode(), str(value).encode()))
                await send(
                    {
                        "type": "http.response.start",
                        "status": result.status,
                        "headers": headers,
                    }
                )
                await send(
                    {"type": "http.response.body", "body": result.content.encode()}
                )
            elif result == Skip:
                continue
            return
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": "404: Not Found".encode()})

    def running(self, func: Callable[[], Any]) -> Callable[[], Any]:
        self.onRunning = func
        return func

    def run(self):
        try:
            asyncio.run(self._run())
        except KeyboardInterrupt:
            pass

    def use(self, path: str):
        def subdecorator(func: Callable[[Request], Awaitable[Response | type[Skip]]]):
            self.middlewares.append(
                Middleware(self, "*", self._maketemplate(path), func)
            )
            return func

        return subdecorator

    def get(self, path: str):
        def subdecorator(func: Callable[[Request], Awaitable[Response | type[Skip]]]):
            self.middlewares.append(
                Middleware(self, "GET", self._maketemplate(path), func)
            )
            return func

        return subdecorator

    def post(self, path: str):
        def subdecorator(func: Callable[[Request], Awaitable[Response | type[Skip]]]):
            self.middlewares.append(
                Middleware(self, "POST", self._maketemplate(path), func)
            )
            return func

        return subdecorator

    def put(self, path: str):
        def subdecorator(func: Callable[[Request], Awaitable[Response | type[Skip]]]):
            self.middlewares.append(
                Middleware(self, "PUT", self._maketemplate(path), func)
            )
            return func

        return subdecorator

    def patch(self, path: str):
        def subdecorator(func: Callable[[Request], Awaitable[Response | type[Skip]]]):
            self.middlewares.append(
                Middleware(self, "PATCH", self._maketemplate(path), func)
            )
            return func

        return subdecorator

    def delete(self, path: str):
        def subdecorator(func: Callable[[Request], Awaitable[Response | type[Skip]]]):
            self.middlewares.append(
                Middleware(self, "DELETE", self._maketemplate(path), func)
            )
            return func

        return subdecorator

    def static(self, prefix: str, path: str):
        async def _middleware(request: Request):
            rootPath = os.path.abspath(path)
            if request.path == prefix or request.path.startswith(prefix + "/"):
                currentPath = os.path.join(
                    rootPath,
                    request.path.removeprefix(prefix)
                    .replace("/..", "")
                    .replace("/.", "")
                    .lstrip("/"),
                )
                if os.path.exists(currentPath):
                    if os.path.isdir(currentPath):
                        currentPath = os.path.join(currentPath, "index.html")
                    if os.path.exists(currentPath):
                        return Response(request).file(currentPath)
            return Skip

        self.get(prefix)(_middleware)
        self.get(re.sub(r"/+", "/", prefix + "/*", 0))(_middleware)
        return self


class Request:
    def __init__(
        self,
        server: Server,
        scope: HTTPScope,
        receive: ASGIReceiveCallable,
        params: dict[str, str],
    ):
        self.server = server
        self._scope = scope
        self._receive = receive
        self.method = scope["method"]
        self.path = scope["path"]
        self.params = params
        self.headers: dict[str, str] = {}
        for header in scope["headers"]:
            self.headers[header[0].decode("utf-8")] = header[1].decode("utf-8")
        self.query: dict[str, str | bool] = {}
        queries = self._scope["query_string"].decode("utf-8").split("&")
        for query in queries:
            parts = query.split("=")
            amount = len(parts)
            name = urllib.parse.unquote(parts.pop(0))
            self.query[name] = (
                True if amount < 2 else urllib.parse.unquote("=".join(parts))
            )

    async def _body(self):
        body = b""
        more_body = True
        while more_body:
            message = await self._receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)
        return body

    async def text(self):
        return (await self._body()).decode("utf-8")

    async def json(self) -> dict[str, str | bool]:
        if self.headers["content-type"] == "application/x-www-form-urlencoded":
            body: dict[str, str | bool] = {}
            queries = (await self.text()).split("&")
            for query in queries:
                parts = query.split("=")
                amount = len(parts)
                name = urllib.parse.unquote(parts.pop(0))
                body[name] = (
                    True if amount < 2 else urllib.parse.unquote("=".join(parts))
                )
            return body
        else:
            return json.loads(await self.text())


class Response:
    def __init__(
        self, request: Request, status: int = 200, headers: dict[str, str | int] = {}
    ):
        self.request = request
        self.status = status
        self.headers = headers
        self.content = ""

    def text(self, content: str):
        self.content = content
        self.headers["content-type"] = "text/plain"
        return self

    def json(self, content: dict[Any, Any]):
        self.content = json.dumps(content, indent=2)
        self.headers["content-type"] = "application/json"
        return self

    def html(self, content: str):
        self.content = content
        self.headers["content-type"] = "text/html"
        return self

    def file(self, path: str):
        with open(path, "r") as file:
            self.content = file.read()
        self.headers["content-type"] = mimetypes.guess_type(path)[0] or "text/plain"
        return self


class Skip:
    pass


class Middleware:
    def __init__(
        self,
        server: Server,
        method: str,
        path: str,
        handler: Callable[[Request], Awaitable[Response | type[Skip]]],
    ):
        self.server = server
        self.method = method
        self.path = path
        self.handler = handler
