from typing import Iterable

from pyee import EventEmitter
from sorcery import delegate_to_attr, dict_of

from gen_net.abstract import AbstractObject, Field
from gen_net.messages import Message
from gen_net.types import Role


class GenAgent(AbstractObject):
    role: Role = Field(
        default="user", description="used to set the role for messages from this node"
    )
    description: str = Field(default="")
    event_emitter: EventEmitter = Field(default_factory=EventEmitter, exclude=True)
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.description and self.__class__.__doc__:
            self.description = self.__class__.__doc__

    def draft_message(self, content: str, method: str, **kwargs) -> Message:
        """Helper method for creating a message with the node's role and id."""
        return Message(
            sender=self, role=self.role, method=method, content=content, **kwargs
        )

    receivable_messages: set[type[Message]] = Field(
        default_factory=set,
        description="set of methodsthat this node can receive",
    )

    @property
    def receivable_methods(self):
        return {message.method for message in self.receivable_messages}

    def receive(self, message: Message) -> Iterable[Message]:
        self.emit("receive", message)

        generator = getattr(self, message.method)
        for reply in generator(message):
            if (yield reply) is StopIteration:
                break
            self.emit("reply", reply)

    @classmethod
    def init_fn(cls):
        schema = cls.schema()

        name = cls.__name__
        description = cls.__doc__
        parameters = schema["properties"]
        required = schema["required"]

        return dict_of(name, description, parameters, required)

    @property
    def receive_fn(self):
        return {
            "name": self.id,
            "description": self.description,
            "parameters": {
                "title": "message",
                "type": "object",
                "oneOf": [
                    message_class.schema() for message_class in self.receivable_messages
                ],
            },
            "required": ["message"],
        }


class AssistantAgent(GenAgent):
    """Helper class for nodes whose messages should be set to role = assistant."""

    role = "assistant"


class SystemAgent(GenAgent):
    """Helper class for nodes whose messages should be set to role = system."""

    role = "system"
