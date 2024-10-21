import socket
import uvicorn
from collections.abc import Awaitable, Callable
from typing import Self, Any
from uvicorn._types import ASGIReceiveCallable, HTTPScope

class _PatchedUvServer(uvicorn.Server):
  def __init__(self, config: uvicorn.Config) -> None:
    ...
  
  async def startup(self, sockets: list[socket.socket] | None = ...) -> None:
    ...
  


class Server:
  def __init__(self, port: str | int | None = ..., debug: bool = ...) -> None:
    ...
  
  def running(self, func: Callable[[], Any]) -> Callable[[], Any]:
    ...
  
  def run(self) -> None:
    ...
  
  def use(self, path: str) -> Callable[..., Callable[[Request], Awaitable[Response | type[Skip]]]]:
    ...
  
  def get(self, path: str) -> Callable[..., Callable[[Request], Awaitable[Response | type[Skip]]]]:
    ...
  
  def post(self, path: str) -> Callable[..., Callable[[Request], Awaitable[Response | type[Skip]]]]:
    ...
  
  def put(self, path: str) -> Callable[..., Callable[[Request], Awaitable[Response | type[Skip]]]]:
    ...
  
  def patch(self, path: str) -> Callable[..., Callable[[Request], Awaitable[Response | type[Skip]]]]:
    ...
  
  def delete(self, path: str) -> Callable[..., Callable[[Request], Awaitable[Response | type[Skip]]]]:
    ...
  
  def static(self, prefix: str, path: str) -> Self:
    ...
  


class Request:
  def __init__(self, server: Server, scope: HTTPScope, receive: ASGIReceiveCallable, params: dict[str, str]) -> None:
    ...
  
  async def text(self) -> str | Any:
    ...
  
  async def json(self) -> dict[str, str | bool]:
    ...
  


class Response:
  def __init__(self, request: Request, status: int = ..., headers: dict[str, str | int] = ...) -> None:
    ...
  
  def text(self, content: str) -> Self:
    ...
  
  def json(self, content: dict[Any, Any]) -> Self:
    ...
  
  def html(self, content: str) -> Self:
    ...
  
  def file(self, path: str) -> Self:
    ...
  


class Skip:
  ...


class Middleware:
  def __init__(self, server: Server, method: str, path: str, handler: Callable[[Request], Awaitable[Response | type[Skip]]]) -> None:
    ...