import re
from abc import ABC
from collections.abc import Iterable
from datetime import datetime
from functools import partial
from textwrap import dedent
from typing import Any
from uuid import uuid4

from beartype import beartype
from beartype.typing import Callable, Optional, TypeVar
from deepmerge import always_merger
from pydantic import UUID4, BaseModel, Field
from pyee import EventEmitter
from sorcery import delegate_to_attr, maybe


class EphemeralObject(BaseModel, ABC):
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
        return self.json()

    @classmethod
    def lift(cls, instance: "EphemeralObject", **kwargs):
        attrs = instance.dict()

        cls.Config.deepmerge(attrs, kwargs)

        return cls(**attrs)


EphemeralObject.Config.json_encoders = {
    EphemeralObject: lambda o: {"cls": o.__class__.__name__, "id": o.id}
}


agent_lookup: dict[UUID4, "EphemeralActor"] = {}
message_lookup: dict[UUID4, "EphemeralMessage"] = {}


def message_hydrator(m: "EphemeralMessage"):
    match m.parent:
        case EphemeralMessage() as m:
            message_lookup[m.id] = m
        case EphemeralObject() as o:
            m.parent = message_lookup[o.id]

    match m.sender:
        case EphemeralActor() as a:
            agent_lookup[a.id] = a
        case EphemeralObject() as o:
            m.sender = agent_lookup[o.id]

    match m.receiver:
        case EphemeralActor() as a:
            agent_lookup[a.id] = a
        case EphemeralObject() as o:
            m.receiver = agent_lookup[o.id]

    return m


class EphemeralMessage(EphemeralObject):
    class Config(EphemeralObject.Config):
        hydrator = message_hydrator

    @classmethod
    def infer_intent(cls, _pattern=re.compile(r"(?<!^)(?=[A-Z])")):
        return re.sub(_pattern, "_", cls.__name__).lower()

    @classmethod
    def reply_to(cls, message: "EphemeralMessage", **kwargs):
        attrs = {
            "sender": message.receiver,
            "receiver": message.sender,
            "parent": message,
        }
        attrs.update(kwargs)
        return cls.lift(message, **attrs)

    @classmethod
    def forward(
        cls, message: "EphemeralMessage", to: Optional[EphemeralObject] = None, **kwargs
    ) -> "EphemeralMessage":
        attrs = {"sender": message.receiver, "receiver": to, "parent": message}
        attrs.update(kwargs)
        return cls.lift(message, **attrs)

    intent: str = Field(include=True)
    context: dict = Field(
        default_factory=dict,
        description="data to pass through the message chain",
        include=True,
    )

    created_at: datetime = Field(default_factory=datetime.utcnow, include=True)
    sender: Optional["EphemeralObject"] = Field(default=None, include=True)
    receiver: Optional["EphemeralObject"] = Field(default=None, include=True)
    parent: Optional["EphemeralMessage"] = Field(default=None, include=True)

    def __init__(self, **kwargs):
        kwargs["intent"] = self.infer_intent()
        kwargs["system"] = kwargs.pop("system", self.__class__.__doc__) or ""
        super().__init__(**kwargs)
        self.__class__.Config.hydrator(self)

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
        return self.json(exclude={"parent"})

    def forward_to(self, to: Optional[EphemeralObject] = None, **kwargs):
        return self.forward(self, to=to, **kwargs)


T = TypeVar("T", bound=EphemeralMessage)
Reply = Optional[T] | Iterable[T]


class EphemeralAgent(EphemeralObject, ABC):
    language: Callable = Field(description="the language model", exclude=True)
    short_term_memory: Any = Field(description="volatile, short-term memory")
    long_term_memory: Any = Field(description="durable, long-term memory")


class EphemeralActor(EphemeralObject):
    system: str = Field(default="", include=True)
    cognition: Optional[EphemeralAgent] = Field(exclude=True)
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
        listens_to,
        on,
        once,
        remove_all_listeners,
        remove_listener,
    ) = delegate_to_attr("event_emitter")

    receivable_messages: set[type[EphemeralMessage]] = Field(
        default_factory=set,
        description="set of intents that this agent can receive",
        exclude=True,
    )

    @classmethod
    def inherited_receivable_messages(cls):
        messages = set()
        for base in cls.__bases__:
            if issubclass(base, EphemeralActor):
                if base_messages := base.__fields__["receivable_messages"].default:
                    messages = messages.union(base_messages)
                messages = messages.union(base.inherited_receivable_messages())
        return messages

    def __init_subclass__(cls):
        super().__init_subclass__()
        f = cls.__fields__["receivable_messages"]
        if f.default:
            f.default = f.default.union(cls.inherited_receivable_messages())

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system = dedent(self.system) or self.__class__.__doc__ or ""

    def __call__(self, message: EphemeralMessage) -> Reply[EphemeralMessage]:
        return self.receive(message)

    def receive(self, message: EphemeralMessage) -> Reply[EphemeralMessage]:
        self.emit("receive", message)

        response = getattr(self, message.intent)(message)

        match response:
            case EphemeralMessage():
                yield response
            case Iterable():
                yield from response


EphemeralObject.update_forward_refs()
EphemeralMessage.update_forward_refs()

Applicator = Callable[[EphemeralMessage], Iterable[EphemeralMessage]]


@beartype
def apply(message: EphemeralMessage) -> Iterable[EphemeralMessage]:
    agent: Optional[EphemeralActor] = message.receiver
    if not agent:
        return []
    yield from agent.receive(message)


@beartype
def propogate(
    message: EphemeralMessage, applicator: Applicator = apply
) -> Iterable[EphemeralMessage]:
    for reply in applicator(message):
        yield reply
        yield from propogate(reply)


@beartype
def propogate_all(messages: Iterable[EphemeralMessage], applicator: Applicator = apply):
    mapper = partial(propogate, applicator=applicator)
    for generator in map(mapper, messages):
        yield from generator()
