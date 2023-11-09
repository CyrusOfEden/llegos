import re
from collections.abc import Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import Literal, Sequence
from uuid import uuid4

from beartype.typing import Callable, Optional
from deepmerge import always_merger
from networkx import DiGraph, MultiGraph
from pydantic import UUID4, BaseModel, Field
from pyee import EventEmitter
from sorcery import delegate_to_attr, maybe


class Object(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        deepmerge = always_merger.merge
        extra = "allow"

    id: UUID4 = Field(default_factory=uuid4, include=True)
    metadata: dict = Field(default_factory=dict, exclude=True)

    def __hash__(self):
        return hash(self.id.bytes)

    def dict(self, *args, exclude_none: bool = True, **kwargs):
        return super().dict(*args, exclude_none=exclude_none, **kwargs)

    def __str__(self):
        return self.json(sort_keys=False)

    @classmethod
    def lift(cls, instance: "Object", **kwargs):
        attrs = instance.dict()

        cls.Config.deepmerge(attrs, kwargs)

        for field in cls.__fields__.values():
            if field.default:
                attrs[field.name] = field.default

        return cls(**attrs)


Object.Config.json_encoders = {
    Object: lambda o: {"cls": o.__class__.__name__, "id": o.id}
}
Object.update_forward_refs()


class State(Object):
    ...


class Actor(Object):
    event_emitter: EventEmitter = Field(
        default_factory=EventEmitter,
        description="emitting events blocks until all listeners have executed",
        exclude=True,
    )
    (
        add_listener,
        emit,
        event_names,
        listeners,
        on,
        once,
        remove_all_listeners,
        remove_listener,
    ) = delegate_to_attr("event_emitter")

    receivable_messages: set[type["Message"]] = Field(
        default_factory=set,
        description="set of intents that this agent can receive",
        exclude=True,
    )

    @classmethod
    def inherited_receivable_messages(cls):
        messages = set()
        for base in cls.__bases__:
            if not issubclass(base, Actor):
                continue
            if base_messages := base.__fields__["receivable_messages"].default:
                messages = messages.union(base_messages)
        return messages

    def __init_subclass__(cls):
        super().__init_subclass__()
        f = cls.__fields__["receivable_messages"]
        if f.default:
            f.default = f.default.union(cls.inherited_receivable_messages())

    def __call__(self, message: "Message"):
        return self.instruct(message)

    def instruct(self, message: "Message") -> Iterable["Message"]:
        self.emit("receive", message)

        response = getattr(self, f"on_{message.intent}")(message)

        match response:
            case Message():
                yield response
            case Iterable():
                yield from response

    @property
    def scene(self):
        return scene_context.get()

    @property
    def relationships(self) -> list["Actor"]:
        edges = [
            (neighbor, key, data)
            for (node, neighbor, key, data) in self.scene.graph.edges(
                keys=True, data=True
            )
            if node == self
        ]
        edges.sort(key=lambda edge: edge[2].get("weight", 1))
        return [actor for (actor, _, _) in edges]

    def receivers(self, *messages: type["Message"]):
        return [
            actor
            for actor in self.relationships
            if all(m in actor.receivable_messages for m in messages)
        ]


Actor.update_forward_refs()


class Scene(Actor):
    graph: MultiGraph = Field(default_factory=MultiGraph, include=False, exclude=True)

    def __contains__(self, key: str | Actor) -> bool:
        match key:
            case str():
                return key in self.lookup
            case Actor():
                return key in self.graph
            case _:
                raise TypeError(f"lookup key must be str or Actor, not {type(key)}")

    @property
    def lookup(self):
        return {a.id: a for a in self.graph.nodes}

    @contextmanager
    def env(self):
        try:
            key = scene_context.set(self)
            yield self
        finally:
            scene_context.reset(key)


scene_context = ContextVar[Scene]("llegos.scene")


class Message(Object):
    @classmethod
    def infer_intent(cls, _pattern=re.compile(r"(?<!^)(?=[A-Z])")):
        return re.sub(_pattern, "_", cls.__name__).lower()

    @classmethod
    def to(cls, receiver: "Object", **kwargs):
        attrs = {"receiver": receiver}
        attrs.update(kwargs)
        return cls(**attrs)

    @classmethod
    def reply_to(cls, message: "Message", **kwargs):
        attrs = {
            "sender": message.receiver,
            "receiver": message.sender,
            "parent": message,
        }
        attrs.update(kwargs)
        return cls.lift(message, **attrs)

    @classmethod
    def forward(
        cls, message: "Message", to: Optional[Object] = None, **kwargs
    ) -> "Message":
        attrs = {"sender": message.receiver, "receiver": to, "parent": message}
        attrs.update(kwargs)
        return cls.lift(message, **attrs)

    content: str = Field(include=True, default="")
    role: Literal["user", "assistant", "system"] = Field(default="user", include=True)

    created_at: datetime = Field(default_factory=datetime.utcnow, include=True)
    sender: Optional["Object"] = Field(default=None, include=True)
    receiver: Optional["Object"] = Field(default=None, include=True)
    parent: Optional["Message"] = Field(default=None, include=True)

    intent: str = Field(include=True)
    context: dict = Field(
        default_factory=dict,
        description="data to pass through the message chain",
        include=True,
    )

    def __init__(self, **kwargs):
        kwargs["intent"] = self.infer_intent()
        super().__init__(**kwargs)

    @property
    def sender_id(self) -> Optional[UUID4]:
        return maybe(self.sender).id

    @property
    def receiver_id(self) -> Optional[UUID4]:
        return maybe(self.receiver).id

    @property
    def parent_id(self) -> Optional[UUID4]:
        return maybe(self.parent).id

    def __str__(self):
        return self.json(exclude={"parent"}, sort_keys=False)

    def forward_to(self, to: Optional[Object] = None, **kwargs):
        return self.forward(self, to=to, **kwargs)


Message.update_forward_refs()


def message_chain(message: Message | None, height: int = 12) -> Iterable[Message]:
    if message is None:
        return []
    elif height > 1:
        yield from message_chain(message.parent, height - 1)
    yield message


def message_list(message: Message, height: int = 12) -> list[Message]:
    return list(message_chain(message, height))


def message_tree(messages: Iterable[Message]):
    g = DiGraph()
    for message in messages:
        if message.parent:
            g.add_edge(message.parent, message)
    return g


def find_closest(
    cls_or_tuple: Sequence[type[Message]] | type[Message],
    of_message: Message,
    max_height: int = 256,
):
    if max_height <= 0:
        raise ValueError("max_height must be positive")
    if max_height == 0:
        raise ValueError("ancestor not found")
    if not of_message.parent:
        return None
    elif isinstance(of_message.parent, cls_or_tuple):
        return of_message.parent
    else:
        return find_closest(of_message.parent, cls_or_tuple, max_height - 1)


def message_path(
    message: Message, ancestor: Message, max_height: int = 256
) -> Iterable[Message]:
    if max_height <= 0:
        raise ValueError("max_height most be positive")
    if max_height == 1 and message.parent is None or message.parent != ancestor:
        raise ValueError("ancestor not found")
    elif message.parent and message.parent != ancestor:
        yield from message_path(message.parent, ancestor, max_height - 1)
    yield message


def send(message: Message) -> Iterable[Message]:
    agent: Optional[Actor] = message.receiver
    if not agent:
        return []
    yield from agent.instruct(message)


def send_and_propogate(
    message: Message, applicator: Callable[[Message], Iterable[Message]] = send
) -> Iterable[Message]:
    for reply in applicator(message):
        yield reply
        yield from send_and_propogate(reply)
