import typing as t
from abc import ABC
from functools import cached_property, lru_cache, partial
from inspect import iscoroutinefunction

import pendulum
from aiolimiter import AsyncLimiter
from anyio import create_memory_object_stream, fail_after, to_process, to_thread
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from ksuid import Ksuid
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from pydash import identity, snake_case
from pyee.asyncio import AsyncIOEventEmitter as EventEmitter

from .logger import getLogger

logger = getLogger("dev")


def namespaced_ksuid(prefix: str):
    return f"{prefix}_{Ksuid()}"


class AbstractObject(BaseModel, ABC):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def cast[T: "AbstractObject"](self, cls: type[T]) -> T:
        return t.cast(cls, self)


class Mailbox(AbstractObject):
    _stream = PrivateAttr(default_factory=partial(create_memory_object_stream, 512))

    @property
    def messages(self) -> MemoryObjectReceiveStream:
        return self._stream[1]

    @property
    def _send_stream(self) -> MemoryObjectSendStream:
        return self._stream[0]

    def send_nowait(self, msg) -> None:
        self._send_stream.send_nowait(msg)

    async def sent(self, msg) -> None:
        await self._send_stream.send(msg)


class Message(AbstractObject):
    model_config = ConfigDict(frozen=True, extra="allow", arbitrary_types_allowed=True)

    id: str = Field(default_factory=partial(namespaced_ksuid, prefix="msg"))
    created_at: pendulum.DateTime = Field(
        default_factory=partial(pendulum.now, pendulum.UTC)
    )

    @classmethod
    @lru_cache(maxsize=1024)
    def intent(cls) -> str:
        return snake_case(cls.__name__.split(".")[-1])


type Concurrency = t.Literal["sync", "async", "thread", "process"]


async def concurrent_handler[
    M: Message, R
](fun: t.Callable[[M], R], msg: M, concurrency: t.Optional[Concurrency] = None) -> R:
    if concurrency == "async" or iscoroutinefunction(fun):
        return await fun(msg)
    elif concurrency == "thread":
        return await to_thread.run_sync(fun, msg, cancellable=True)
    elif concurrency == "process":
        return await to_process.run_sync(fun, msg, cancellable=True)
    else:
        return fun(msg)


class ReservedMessageClassName(ValueError):
    ...


class MissingHandler(ValueError):
    ...


class GenServer[S](AbstractObject):
    pid: str = Field(default_factory=partial(namespaced_ksuid, prefix="pid"))
    restart: t.Literal["permanent", "temporary", "transient"] = Field(
        default="permanent",
        description="permanent = always restart, temporary = never restart, transient = restart only if it crashes",
    )
    state: S

    _status: None | t.Literal["running", "stopped", "killed"] = None
    _event_emitter: EventEmitter = PrivateAttr(default_factory=EventEmitter)
    _inbox: Mailbox = PrivateAttr(default_factory=Mailbox)

    @property
    def status(self):
        return self._status

    async def init(self, *args, **kwargs) -> None:
        from pprint import pprint

        print("INIT")
        pprint(args)
        pprint(kwargs)

    async def start(self):
        self._status = "running"
        try:
            async with self._inbox.messages:
                async for msg in self._inbox.messages:
                    if self._status != "running":
                        return

                    match msg:
                        case ("call", msg, concurrency, res):
                            handler = self._intent_handler(msg)
                            res = t.cast(MemoryObjectSendStream, res)
                            response = await concurrent_handler(
                                handler, msg, concurrency
                            )
                            res.send_nowait(response)
                        case ("cast", msg, concurrency):
                            await concurrent_handler(
                                self._intent_handler(msg), msg, concurrency
                            )
                        case ("cast", msg):
                            await concurrent_handler(self._intent_handler(msg), msg)
                        case (tuple() | list()) as args:
                            await self.handle_info(*args)
                        case dict() as kwargs:
                            await self.handle_info(**kwargs)
                        case _ as arg:
                            await self.handle_info(arg)
        except BaseException as error:
            await self.stop("failed", error)

    async def stop(
        self,
        reason="stopped",
        error: BaseException | None = None,
        timeout: float | None = None,
    ):
        self._event_emitter.emit("stop", self, reason, error)
        self._event_emitter.remove_all_listeners("stop")
        self._status = reason
        with fail_after(timeout):
            await self.handle_stop(reason, error)

    async def __call__[
        R
    ](
        self,
        msg: Message,
        timeout: float | None = 5,
        concurrency: t.Optional[Concurrency] = None,
    ) -> R:  # type: ignore
        res_send, res_recv = create_memory_object_stream(1)
        self._inbox.send_nowait(("call", msg, concurrency, res_send))
        with fail_after(timeout):
            async with res_recv:
                response: R = await res_recv.receive()
                return response

    def cast(self, msg: Message, concurrency: t.Optional[Concurrency] = None):
        self._inbox.send_nowait(("cast", msg, concurrency))

    def link(self, server: "GenServer"):
        self._event_emitter.on("stop", server.handle_down)
        server._event_emitter.on("stop", self.handle_down)

    def unlink(self, server: "GenServer"):
        self._event_emitter.remove_listener("stop", server.handle_down)
        server._event_emitter.remove_listener("stop", self.handle_down)

    async def handle_info(self, *args):
        ...

    async def handle_down(self, server: "GenServer", reason: str, error: Exception):
        raise error

    async def handle_stop(self, reason: str, error: BaseException | None):
        if error:
            raise error

    def _intent_handler(self, msg: t.Union[Message, type[Message]]):
        intent = msg.intent()
        if intent in {"call", "cast"}:
            cls = msg.__class__ if isinstance(msg, Message) else msg
            raise ReservedMessageClassName(cls)

        method = f"handle_{intent}"
        if not hasattr(self, method):
            raise MissingHandler(intent)

        return getattr(self, method)


class GenAgent[S](GenServer[S]):
    """
    Public Interface
    """

    async def get_state[
        G
    ](self, fun: t.Callable[[S], G] = identity, timeout: int | None = 5) -> G:
        return await self(self.GetState(fun=fun), timeout)

    async def update_state(
        self, fun: t.Callable[[S], S], timeout: int | None = 5
    ) -> True:
        return await self(self.UpdateState(fun=fun), timeout)

    async def get_and_update_state[
        G
    ](self, fun: t.Callable[[S], tuple[G, S]], timeout: int | None = 5) -> G:
        return await self(self.GetAndUpdateState(fun=fun), timeout)

    """
    Internal Implementation
    """

    class GetState[G](Message):
        fun: t.Callable[[S], G]

    class UpdateState(Message):
        fun: t.Callable[[S], S]

    class GetAndUpdateState[G](Message):
        fun: t.Callable[[S], tuple[G, S]]

    def handle_get_state[G](self, msg: GetState[G]) -> G:
        return msg.fun(self.state)

    async def handle_update_state(self, msg: UpdateState) -> True:
        msg.fun(self.state)
        return True

    async def handle_get_and_update_state[G](self, msg: GetAndUpdateState[G]) -> G:
        got_value = msg.fun(self.state)
        return got_value


class GenSupervisor(GenServer):
    strategy: t.Literal["one_for_one", "one_for_all", "rest_for_one"]
    children: list[GenServer]
    max_restarts: int = 3
    max_seconds: int = 5

    @cached_property
    def _limiter(self):
        return AsyncLimiter(max_rate=self.max_restarts, time_period=self.max_seconds)

    async def start_child(self, server: GenServer):
        self.children.append(server)
        self.link(server)
        await server.start()

    async def stop_child(self, server: GenServer):
        if server not in self.children:
            raise KeyError(server)
        self.unlink(server)
        await server.stop()

    async def restart_child(self, server: GenServer):
        await self.stop_child(server)
        await self.start_child(server)

    async def handle_down(self, server: GenServer, reason: str, error: Exception):
        if not self._limiter.has_capacity():
            await self.stop("failed", error)
            return

        match self.strategy:
            case "one_for_one":
                await self.restart_child(server)
            case "one_for_all":
                for child in self.children:
                    await self.restart_child(child)
            case "rest_for_one":
                index = self.children.index(server)
                for child in self.children[index:]:
                    await self.restart_child(child)


class NameAlreadyExists(ValueError):
    ...


class MissingContext(RuntimeError):
    ...


# class GenSystem(AbstractObject):
#     lookup: dict[str, GenServer] = Field(default_factory=dict)
#     _graph: networkx.Graph = Field(default_factory=networkx.Graph)

#     def register(self, actor: GenServer, name: str | None = None):
#         self._graph.add_node(actor)
#         if name in self.lookup:
#             raise NameAlreadyExists(name)
#         if name:
#             self.lookup[name] = actor

#     def link(self, a: GenServer, b: GenServer):
#         if not self._graph.has_edge(a, b):
#             self._graph.add_edge(a, b)
#             a._link(b)

#     def unlink(self, a: GenServer, b: GenServer):
#         self._graph.remove_edge(a, b)

#     def list(self):
#         self._graph.nodes.values()

#     async def spawn(self, actor: GenServer, *args, **kwargs):
#         if not self._task_group:
#             raise MissingContext()

#         self._task_group.start_soon(actor.run)

#     def send(self, actor: GenServer, msg: Message):
#         ...

#     async def __aenter__(self):
#         self._exitstack = AsyncExitStack()
#         await self._exitstack.__aenter__()
#         self._task_group = await self._exitstack.enter_async_context(
#             create_task_group()
#         )

#     async def __aexit__(self, exc_type, exc_val, exc_tb):
#         return await self._exitstack.__aexit__(exc_type, exc_val, exc_tb)
