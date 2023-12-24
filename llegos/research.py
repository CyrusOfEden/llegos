import shelve
import signal
import typing as t
from collections.abc import Iterable
from contextvars import ContextVar, Token
from datetime import datetime
from typing import Any

from beartype import beartype
from beartype.typing import Callable, Optional
from deepmerge import always_merger
from ksuid import Ksuid
from networkx import DiGraph, MultiGraph
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydash import snake_case
from pyee import EventEmitter
from sorcery import delegate_to_attr, maybe

if t.TYPE_CHECKING:
    from pydantic.main import IncEx


def namespaced_ksuid(prefix: str):
    return f"{prefix}_{Ksuid()}"


def namespaced_ksuid_generator(prefix: str):
    return lambda: namespaced_ksuid(prefix)


class ShelfWrapper:
    path = ".llegos.db"
    _instance: Optional["ShelfWrapper"] = None
    _shelf: Optional[shelve.Shelf] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self):
        if self._shelf is None:
            shelf = shelve.open(self.path)
            self._shelf = shelf
            signal.signal(signal.SIGTERM, lambda *_: shelf.close())
        return self._shelf

    def get(self, key: str, default: Any = None) -> Any:
        return self.load().get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self.load()

    def __getitem__(self, key: str) -> Any:
        return getattr(self.load(), key)

    def __setitem__(self, key: str, value: Any):
        self.load()[key] = value


Shelf = ShelfWrapper()


class Object(BaseModel):
    @classmethod
    def lift(cls, instance: "Object", **kwargs):
        attrs = instance.model_dump()
        always_merger.merge(attrs, kwargs)

        for field, info in cls.model_fields.items():
            if field in attrs:
                continue

            attrs[field] = info.get_default(call_default_factory=True)

        return cls(**attrs)

    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.model_fields["id"].default_factory = namespaced_ksuid_generator(
            snake_case(cls.__name__)
        )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="allow",
    )

    id: str = Field(default_factory=namespaced_ksuid_generator("object"))
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def hydrate(self):
        for field in self.model_fields_set:
            if field in {"id", "metadata"}:
                continue

            info = self.model_fields[field]
            if not isinstance(info.annotation, type) or isinstance(
                info.annotation, t.GenericAlias
            ):
                continue
            if not issubclass(info.annotation, Object):
                continue

            if obj := getattr(self, field):
                if shelf_obj := Shelf.get(obj.id):
                    setattr(self, field, shelf_obj)
                else:
                    Shelf[obj.id] = obj
        return self

    def model_dump_json(
        self,
        *,
        indent: int | None = None,
        include: "IncEx" = None,
        exclude: "IncEx" = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = True,  # This is the only change
        round_trip: bool = False,
        warnings: bool = True,
    ) -> str:
        return super().model_dump_json(
            indent=indent,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
        )

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return self.model_dump_json()


class MissingScene(ValueError):
    ...


class Actor(Object):
    _event_emitter = EventEmitter()
    _receivable_messages: set[type["Message"]] = set()

    @classmethod
    def _inherited_receivable_messages(cls):
        messages = set()
        for base in cls.__bases__:
            if not issubclass(base, Actor):
                continue
            if base_messages := base._receivable_messages:
                if not isinstance(base_messages, set):
                    base_messages = base_messages.default
                messages = messages.union(base_messages)
        return messages

    def __init_subclass__(cls):
        super().__init_subclass__()
        if cls_receivable_messages := cls._receivable_messages:
            if not isinstance(cls_receivable_messages, set):
                cls_receivable_messages = cls_receivable_messages.default

            cls._receivable_messages = cls_receivable_messages.union(
                cls._inherited_receivable_messages()
            )

    def __call__(self, message: "Message") -> Iterable["Message"]:
        return self.send(message)

    def send(self, message: "Message") -> Iterable["Message"]:
        self.emit("before:receive", message)

        intent = snake_case(message.__class__.__name__)
        response = getattr(self, f"receive_{intent}")(message)

        match response:
            case Message():
                yield response
            case Iterable():
                yield from response

        self.emit("after:receive", message)

    @property
    def scene(self):
        if scene := scene_context.get():
            return scene
        raise MissingScene(self)

    @property
    def relationships(self) -> list["Actor"]:
        edges = [
            (neighbor, key, data)
            for (node, neighbor, key, data) in self.scene._graph.edges(
                keys=True,
                data=True,
            )
            if node != self
        ]
        edges.sort(key=lambda edge: edge[2].get("weight", 1))
        return [actor for (actor, _, _) in edges]

    def receivers(self, *messages: type["Message"]):
        return [
            actor
            for actor in self.relationships
            if all(m in actor._receivable_messages for m in messages)
        ]

    (
        add_listener,
        emit,
        event_names,
        listeners,
        on,
        once,
        remove_all_listeners,
        remove_listener,
    ) = delegate_to_attr("_event_emitter")


class Scene(Actor):
    _graph = MultiGraph()
    _context_key: Optional[Token["Scene"]]

    def __contains__(self, key: str | Actor) -> bool:
        match key:
            case str():
                return key in self.lookup
            case Actor():
                return key in self._graph
            case _:
                raise TypeError(f"lookup key must be str or Actor, not {type(key)}")

    @property
    def lookup(self):
        return {a.id: a for a in self._graph.nodes}

    def __enter__(self):
        self._context_key = scene_context.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        scene_context.reset(self._context_key)
        self._context_key = None


scene_context = ContextVar[Scene]("llegos.scene")


class Message(Object):
    @classmethod
    def reply_to(cls, message: "Message", **kwargs):
        kwargs.update(
            {
                "sender": message.receiver,
                "receiver": message.sender,
                "parent": message,
            }
        )
        return cls.lift(message, **kwargs)

    @classmethod
    def forward(cls, message: "Message", receiver: Actor, **kwargs) -> "Message":
        kwargs.update(
            {
                "sender": message.receiver,
                "receiver": receiver,
                "parent": message,
            }
        )
        return cls.lift(message, **kwargs)

    created_at: datetime = Field(default_factory=datetime.utcnow, frozen=True)
    sender: Actor
    receiver: Actor
    parent: Optional["Message"] = Field(default=None)

    @property
    def sender_id(self) -> str:
        return self.sender.id

    @sender_id.setter
    def sender_id(self, value: str):
        Shelf[self.sender.id] = self.sender
        self.sender = Shelf[value]

    @property
    def receiver_id(self) -> str:
        Shelf[self.receiver.id] = self.receiver
        return self.receiver.id

    @receiver_id.setter
    def receiver_id(self, value: str):
        self.receiver = Shelf[value]

    @property
    def parent_id(self) -> Optional[str]:
        if parent := self.parent:
            Shelf[parent.id] = parent
            return maybe(parent).id
        return None

    @parent_id.setter
    def parent_id(self, value: str):
        self.parent = Shelf[value]

    def __str__(self):
        return self.model_dump_json(exclude={"parent"})

    def forward_to(self, receiver: Actor, **kwargs):
        return self.forward(self, receiver, **kwargs)

    def reply(self, **kwargs):
        return self.reply_to(self, **kwargs)


@beartype
def message_chain(message: Message | None, height: int) -> Iterable[Message]:
    if message is None:
        return []
    elif height > 1:
        yield from message_chain(message.parent, height - 1)
    yield message


@beartype
def message_list(message: Message, height: int) -> list[Message]:
    return list(message_chain(message, height))


@beartype
def message_tree(messages: Iterable[Message]):
    g = DiGraph()
    for message in messages:
        if message.parent:
            g.add_edge(message.parent, message)
    return g


class MessageNotFound(ValueError):
    ...


@beartype
def message_ancestor(
    cls_or_tuple: tuple[type[Message]] | type[Message],
    of_message: Message,
    max_height: int = 256,
):
    if max_height <= 0:
        raise ValueError("max_height must be positive")
    if max_height == 0:
        raise MessageNotFound(cls_or_tuple)
    if not of_message.parent:
        return None
    elif isinstance(of_message.parent, cls_or_tuple):
        return of_message.parent
    elif parent := of_message.parent:
        return message_ancestor(cls_or_tuple, parent, max_height - 1)


@beartype
def message_path(
    message: Message, ancestor: Message, max_height: int = 256
) -> Iterable[Message]:
    if max_height <= 0:
        raise ValueError("max_height most be positive")
    if max_height == 1 and message.parent is None or message.parent != ancestor:
        raise MessageNotFound(ancestor)
    elif message.parent and message.parent != ancestor:
        yield from message_path(message.parent, ancestor, max_height - 1)
    yield message


class InvalidReceiver(ValueError):
    ...


class MissingReceiver(ValueError):
    ...


@beartype
def send(message: Message) -> Iterable[Message]:
    if message.__class__ in message.receiver._receivable_messages:
        yield from message.receiver.send(message)
    raise InvalidReceiver(message)


@beartype
def send_and_propogate(
    message: Message, applicator: Callable[[Message], Iterable[Message]] = send
) -> Iterable[Message]:
    for reply in applicator(message):
        if reply:
            yield reply
            yield from send_and_propogate(reply)


Object.model_rebuild()
Message.model_rebuild()
