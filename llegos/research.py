import typing as t
from collections.abc import Iterable
from contextvars import ContextVar, Token
from datetime import datetime

from beartype import beartype
from beartype.typing import Callable, Optional
from deepmerge import always_merger
from ksuid import Ksuid
from networkx import DiGraph, MultiGraph
from pydantic import BaseModel, ConfigDict, Field
from pydash import snake_case
from pyee import EventEmitter
from sorcery import delegate_to_attr, maybe

if t.TYPE_CHECKING:
    from pydantic.main import IncEx


def namespaced_ksuid(prefix: str):
    return f"{prefix}_{Ksuid()}"


def namespaced_ksuid_generator(prefix: str):
    return lambda: namespaced_ksuid(prefix)


class Object(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="allow",
    )

    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.model_fields["id"].default_factory = namespaced_ksuid_generator(
            snake_case(cls.__name__)
        )

    id: str = Field(default_factory=namespaced_ksuid_generator("object"))
    metadata: dict = Field(default_factory=dict)

    def model_dump_json(
        self,
        *,
        indent: int | None = None,
        include: "IncEx" = None,
        exclude: "IncEx" = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = True,  # updated default to True to reduce JSON noise sent to the LLM
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

    def __setattr__(self, name: str, value: t.Any) -> None:
        match value:
            case Object():
                object.__setattr__(self, name, value)
            case _:
                super().__setattr__(name, value)

    @classmethod
    def lift(cls, instance: "Object", **kwargs):
        attrs = instance.model_dump()
        always_merger.merge(attrs, kwargs)
        return cls(**attrs)


class MissingScene(ValueError):
    ...


class InvalidMessage(ValueError):
    ...


class Actor(Object):
    _event_emitter = EventEmitter()

    def __call__(self, message: "Message") -> Iterable["Message"]:
        return self.send(message)

    def can_receive(self, message: "Message") -> bool:
        return True

    def send(self, message: "Message") -> Iterable["Message"]:
        if not self.can_receive(message):
            raise InvalidMessage(message)

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
            if all(actor.can_receive(m) for m in messages)
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
    actors: t.Sequence[Actor] = Field(default_factory=list)
    _graph = MultiGraph()

    def __getitem__(self, key: str | Actor | t.Any) -> Actor:
        match key:
            case str():
                return self.directory[key]
            case _:
                raise TypeError("__getitem__ accepts a key of str", key)

    def __contains__(self, key: str | Actor | t.Any) -> bool:
        match key:
            case str():
                return key in self.directory
            case Actor():
                return key in self.actors
            case _:
                raise TypeError("__contains__ accepts a key of str or Actor", key)

    @property
    def directory(self):
        return {a.id: a for a in self.actors}

    def __enter__(self):
        global scene_token, scene_context
        scene_token = scene_context.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global scene_token, scene_context
        if scene_token:
            scene_context.reset(scene_token)
            scene_token = None


scene_context = ContextVar[Scene]("llegos.scene")
scene_token: Optional[Token[Scene]] = None


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
    sender: t.ForwardRef("Actor")
    receiver: t.ForwardRef("Actor")
    parent: Optional[t.ForwardRef("Message")] = None

    @property
    def sender_id(self) -> str:
        return self.sender.id

    @property
    def receiver_id(self) -> str:
        return self.receiver.id

    @property
    def parent_id(self) -> Optional[str]:
        return maybe(self.parent).id

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


class MissingReceiver(ValueError):
    ...


@beartype
def send_message(message: Message) -> Iterable[Message]:
    if not message.receiver:
        raise MissingReceiver(message)
    yield from message.receiver.send(message)


@beartype
def propogate_message(
    message: Message, applicator: Callable[[Message], Iterable[Message]] = send_message
) -> Iterable[Message]:
    for reply in applicator(message):
        if reply:
            yield reply
            yield from propogate_message(reply, applicator)


Object.model_rebuild()
Message.model_rebuild()
Actor.model_rebuild()
Scene.model_rebuild()
