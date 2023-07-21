from typing import Iterable, Optional

from pyee import EventEmitter
from sorcery import delegate_to_attr, dict_of

from llm_net.abstract import AbstractObject, Field
from llm_net.message import Message
from llm_net.types import Role


class GenAgent(AbstractObject):
    role: Role = Field(description="used to set the role for messages from this node")
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
        description="set of message types that this node can receive",
    )

    def receive(self, message: Optional[Message] = None) -> Iterable[Message]:
        if message is None or message.sender == self or message.receiver != self:
            return None

        self.emit("receive", message)

        method = getattr(self, message.type) if message.type else self.call
        return method(message)

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


class SystemAgent(GenAgent):
    """Helper class for nodes whose messages should be set to role = system."""

    role = "system"


class AssistantAgent(GenAgent):
    """Helper class for nodes whose messages should be set to role = assistant."""

    role = "assistant"


class UserAgent(GenAgent):
    """Helper class for nodes whose messages should be set to role = user."""

    role = "user"
