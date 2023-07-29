from abc import ABC
from collections.abc import Generator
from datetime import datetime
from functools import partial
from textwrap import dedent
from typing import Callable, Iterable, Optional, TypeVar
from uuid import uuid4

import yaml
from networkx import DiGraph
from pydantic import UUID4, BaseModel, Field
from pyee import EventEmitter
from sorcery import delegate_to_attr

from llegos.messages import Intent


class EphemeralObject(BaseModel, ABC):
    class Config:
        arbitrary_types_allowed = True

    id: UUID4 = Field(default_factory=uuid4)
    metadata: dict = Field(default_factory=dict)

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
            "required": schema["required"],
        }


class EphemeralMessage(EphemeralObject):
    """
    Messages are used to send messages between nodes.
    """

    class Config(EphemeralObject.Config):
        arbitrary_types_allowed = True
        json_encoders = {
            EphemeralObject: lambda a: a.id,
        }

    intent: Intent = Field(
        description=dedent(
            """\
            Agents call methods named after the intent of the message.

            A curated set of intents to consider:
            - chat = "chat about this topic", "talk about this topic", etc.
            - request = "request this thing", "ask for this thing", etc.
            - response = "responding with this thing", "replying with this thing", etc.
            - query = "query for information"
            - inform = "inform of new data", "tell about this thing", etc.
            - proxy = "route this message to another agent"
            - step = process the environment, a la multi agent reinforcement learning
            - be = "be this way", "act as if you are", etc.
            - do = "do this thing", "perform this action", etc.
            - check = "check if this is true", "verify this", etc.
            """
        ),
    )
    body: str = Field()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sender: Optional[EphemeralObject] = Field(
        default=None, serialization_alias="sender_id"
    )
    receiver: Optional[EphemeralObject] = Field(
        default=None, serialization_alias="receiver_id"
    )
    reply_to: Optional["EphemeralMessage"] = Field(
        default=None, serialization_alias="reply_to_id"
    )

    @property
    def role(self):
        return self.sender.role

    @classmethod
    def reply(cls, message: "EphemeralMessage", **kwargs) -> "EphemeralMessage":
        attrs = dict(
            sender=message.receiver,
            receiver=message.sender,
            reply_to=message,
            intent=cls.__fields__["intent"].default,
        )
        attrs.update(kwargs)
        return cls(**attrs)

    @classmethod
    def forward(cls, message: "EphemeralMessage", **kwargs) -> "EphemeralMessage":
        attrs = dict(
            sender=message.receiver,
            body=message.body,
            reply_to=message,
            intent=cls.__fields__["intent"].default,
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
    def receivable_intents(self):
        return {
            message.__fields__["intent"].default for message in self.receivable_messages
        }

    def receive(self, message: EphemeralMessage) -> Reply[EphemeralMessage]:
        self.emit(message.intent, message)

        response = getattr(self, message.intent)(message)

        match response:
            case Generator():
                yield from response
            case EphemeralMessage():
                yield response

    @property
    def public_description(self):
        return self.__class__.__doc__

    @property
    def receive_schema(self):
        return {
            "name": str(self.id),
            "description": self.public_description,
            "parameters": {
                "title": "message",
                "type": "object",
                "oneOf": [cls.init_schema for cls in self.receivable_messages],
            },
            "required": ["message"],
        }


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


def message_graph(messages: Iterable[EphemeralMessage]):
    g = DiGraph()
    for message in messages:
        if message.reply:
            g.add_edge(message.reply, message)
    return g
