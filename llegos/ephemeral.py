import re
from abc import ABC
from collections.abc import Generator
from datetime import datetime
from functools import partial
from typing import Callable, Iterable, Optional, TypeVar
from uuid import uuid4

import yaml
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

    @classmethod
    @property
    def init_schema(cls):
        schema = cls.schema()
        if "properties" not in schema:
            schema = schema["definitions"][cls.__name__]

        parameters = {}
        for key, value in schema["properties"].items():
            if key == "id":
                continue
            elif value.get("serialization_alias", "").endswith("_id"):
                parameters[f"{key}_id"] = {
                    "title": value["title"],
                    "type": "string",
                }
            else:
                parameters[key] = value

        return {
            "name": cls.__name__,
            "description": cls.__doc__,
            "parameters": parameters,
            "required": schema.get("required", []),
        }


_camel_case_pattern = re.compile(r"(?<!^)(?=[A-Z])")


class EphemeralMessage(EphemeralObject):
    """
    Messages are used to send messages between nodes.
    """

    class Config(EphemeralObject.Config):
        arbitrary_types_allowed = True
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
        attrs.update(kwargs)
        return cls(**attrs)

    @classmethod
    def reply_to(cls, message: "EphemeralMessage", **kwargs):
        attrs = dict(
            sender=message.receiver,
            receiver=message.sender,
            parent=message,
        )
        attrs.update(kwargs)
        return cls(**attrs)

    @classmethod
    def forward(
        cls, message: "EphemeralMessage", to: Optional[EphemeralObject] = None, **kwargs
    ) -> "EphemeralMessage":
        attrs = dict(
            sender=message.receiver,
            reciever=to,
            body=message.body,
            parent=message,
        )
        attrs.update(kwargs)
        return cls(**attrs)


T = TypeVar("T", bound=EphemeralMessage)
Reply = Optional[T] | Iterable[T]


class EphemeralAgent(EphemeralObject):
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

    @property
    def call_schema(self):
        return {
            "name": str(self.id),
            "description": self.public_description,
            "parameters": {
                "message": {
                    "oneOf": [cls.init_schema for cls in self.receivable_messages]
                },
            },
            "required": ["message"],
        }

    def __call__(self, message: EphemeralMessage) -> Reply[EphemeralMessage]:
        return self.receive(message)

    def receive(self, message: EphemeralMessage) -> Reply[EphemeralMessage]:
        self.emit(message.intent, message)

        response = getattr(self, message.intent)(message)

        match response:
            case Generator():
                yield from response
            case EphemeralMessage():
                yield response

    @property
    def public_description(self) -> str:
        return self.__class__.__doc__ or ""


Applicator = Callable[[EphemeralMessage], Iterable[EphemeralMessage]]


def apply(message: EphemeralMessage) -> Iterable[EphemeralMessage]:
    agent: Optional[EphemeralAgent] = message.receiver
    if not agent:
        return []
    yield from agent.receive(message)


def propogate(
    message: EphemeralMessage, applicator: Applicator = apply
) -> Iterable[EphemeralMessage]:
    for reply in applicator(message):
        yield reply
        yield from propogate(reply)


def propogate_all(messages: Iterable[EphemeralMessage], applicator: Applicator = apply):
    mapper = partial(propogate, applicator=applicator)
    for generator in map(mapper, messages):
        yield from generator()
