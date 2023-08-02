import re
from abc import ABC
from collections.abc import Iterable
from datetime import datetime
from functools import partial
from uuid import uuid4

import deepmerge
import yaml
from beartype import beartype
from beartype.typing import Callable, Optional, TypeVar
from pydantic import UUID4, BaseModel, Field
from pyee import EventEmitter
from sorcery import delegate_to_attr


class EphemeralObject(BaseModel, ABC):
    class Config:
        arbitrary_types_allowed = True
        extra = "allow"

    id: UUID4 = Field(default_factory=uuid4)
    metadata: dict = Field(default_factory=dict, exclude=True)

    def __str__(self):
        return yaml.dump(self.dict(), sort_keys=False)

    def __hash__(self):
        return hash(self.id)


_camel_case_pattern = re.compile(r"(?<!^)(?=[A-Z])")


class EphemeralCognition(EphemeralObject, ABC):
    ...


class EphemeralMessage(EphemeralObject):
    """
    Messages are used to send messages between nodes.
    """

    class Config(EphemeralObject.Config):
        arbitrary_types_allowed = True
        deepmerge = deepmerge.always_merger.merge
        json_encoders = {
            EphemeralObject: lambda a: a.id,
        }

    intent: str = Field(
        description="the method to call on the receiver",
    )
    context: dict = Field(
        default_factory=dict,
        description="data to pass through the message chain",
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    sender: Optional[EphemeralObject] = Field(
        default=None, serialization_alias="sender_id"
    )
    receiver: Optional[EphemeralObject] = Field(
        default=None, serialization_alias="receiver_id"
    )
    parent: Optional["EphemeralMessage"] = Field(
        default=None, serialization_alias="parent_id"
    )

    def __init__(self, **kwargs):
        if "intent" not in kwargs:
            kwargs["intent"] = re.sub(
                _camel_case_pattern, "_", self.__class__.__name__
            ).lower()
        super().__init__(**kwargs)

    @property
    def role(self):
        return self.sender.role

    def forward_to(self, receiver: EphemeralObject):
        return self.__class__.forward(self, to=receiver)

    @classmethod
    def lift(cls, message: "EphemeralMessage", **kwargs):
        attrs = message.dict(exclude={"id", "created_at"})

        for field in cls.__fields__.values():
            if field.default is not None:
                attrs[field.name] = field.default

        cls.Config.deepmerge(attrs, kwargs)
        return cls(**attrs)

    @classmethod
    def reply_to(cls, message: "EphemeralMessage", **kwargs):
        attrs = dict(
            parent=message,
            sender=message.receiver,
            receiver=message.sender,
            context=message.context,
        )

        cls.Config.deepmerge(attrs, kwargs)
        return cls(**attrs)

    @classmethod
    def forward(
        cls, message: "EphemeralMessage", to: Optional[EphemeralObject] = None, **kwargs
    ) -> "EphemeralMessage":
        attrs = dict(
            parent=message,
            sender=message.receiver,
            reciever=to,
            context=message.context,
        )

        cls.Config.deepmerge(attrs, kwargs)
        return cls(**attrs)


T = TypeVar("T", bound=EphemeralMessage)
Reply = Optional[T] | Iterable[T]


class EphemeralAgent(EphemeralObject):
    cognition: EphemeralCognition = Field()
    role: str = Field(
        default="user", description="used to set the role for messages from this node"
    )
    event_emitter: EventEmitter = Field(
        default_factory=EventEmitter,
        exclude=True,
        description="emitting events is blocking",
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
    )

    def __call__(self, message: EphemeralMessage) -> Reply[EphemeralMessage]:
        return self.receive(message)

    def receive(self, message: EphemeralMessage) -> Reply[EphemeralMessage]:
        self.emit(message.intent, message)

        response = getattr(self, message.intent)(message)

        match response:
            case EphemeralMessage():
                yield response
            case Iterable():
                yield from response

    @property
    def public_description(self) -> str:
        return self.__class__.__doc__ or ""


Applicator = Callable[[EphemeralMessage], Iterable[EphemeralMessage]]


@beartype
def apply(message: EphemeralMessage) -> Iterable[EphemeralMessage]:
    agent: Optional[EphemeralAgent] = message.receiver
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
