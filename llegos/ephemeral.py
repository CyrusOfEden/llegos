from abc import ABC
from datetime import datetime
from functools import partial
from textwrap import dedent
from typing import Callable, Iterable, Optional, TypeVar, Union

import yaml
from networkx import DiGraph
from pydantic import BaseModel, Field
from pyee import EventEmitter
from sorcery import delegate_to_attr

from llegos.messages import Intent


class EphemeralObject(BaseModel, ABC):
    class Config:
        arbitrary_types_allowed = True

    metadata: dict = Field(default_factory=dict)

    @property
    def id(self):
        return id(self)

    def __str__(self):
        return yaml.dump(self.dict(), sort_keys=False)

    def __hash__(self):
        return hash(self.id)

    @classmethod
    @property
    def init_schema(cls):
        schema = cls.schema()

        parameters = schema["properties"]
        del parameters["id"]

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

    intent: Union[str, Intent] = Field(
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

    @staticmethod
    def reply(message: "EphemeralMessage", **kwargs) -> "EphemeralMessage":
        update = {
            "sender": message.receiver,
            "receiver": message.sender,
            "reply_to": message,
            "method": "reply",
            **kwargs,
        }
        return message.copy(update)

    @staticmethod
    def forward(message: "EphemeralMessage", **kwargs) -> "EphemeralMessage":
        update = {
            "sender": message.receiver,
            "reply_to": message,
            "body": message.body,
            **kwargs,
        }
        return message.copy(update)

    @classmethod
    @property
    def init_schema(cls):
        schema = super().init_schema()

        params = schema["parameters"]
        for key in ("reply_to", "sender", "receiver"):
            params[key] = {
                "title": params[key]["title"],
                "type": "string",
            }

        return schema


T = TypeVar("T", bound=EphemeralMessage)
Reply = Union[Optional[T], Iterable[T]]


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
        return {message.intent for message in self.receivable_messages}

    def draft_message(self, content: str, method: str, **kwargs) -> EphemeralMessage:
        """Helper method for creating a message with the node's role and id."""
        return EphemeralMessage(
            sender=self, role=self.role, intent=method, content=content, **kwargs
        )

    def receive(self, message: EphemeralMessage) -> Reply[EphemeralMessage]:
        response = getattr(self, message.intent)
        self.emit(message.intent, message)

        match response:
            case Iterable():
                yield from response
            case EphemeralMessage():
                yield response

    @property
    def public_description(self):
        return self.__class__.__doc__

    @property
    def receive_fn(self):
        return {
            "name": self.id,
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
        raise StopIteration
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
