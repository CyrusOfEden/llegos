from typing import Any, Callable, Generator, Iterable, Optional, TypeVar, Union

from pyee import EventEmitter
from sorcery import delegate_to_attr

from gen_net.abstract import AbstractObject, Field
from gen_net.messages import Message
from gen_net.types import Role

T = TypeVar("T", bound=Message)
GenReply = Union[Optional[T], Iterable[T]]


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

    receivable_messages: set[type[Message]] = Field(
        default_factory=set,
        description="set of intents that this agent can receive",
    )

    @property
    def receivable_intents(self):
        return {message.intent for message in self.receivable_messages}

    def draft_message(self, content: str, method: str, **kwargs) -> Message:
        """Helper method for creating a message with the node's role and id."""
        return Message(
            sender=self, role=self.role, intent=method, content=content, **kwargs
        )

    def property(self, message: Message) -> Any:
        """Helper method reading a property."""
        return getattr(self, message.intent)

    def call(self, message: Message) -> Any:
        """Helper method calling a method with no args."""
        return self.property(message)()

    def receive(self, message: Message) -> GenReply[Message]:
        response = getattr(self, message.intent)
        self.emit(message.intent, message)

        match response:
            case Iterable():
                yield from response
            case Message():
                yield response

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


Applicator = Callable[[Message], Iterable[Message]]


def apply(message: Message) -> Iterable[Message]:
    agent = message.receiver
    if not agent:
        raise StopIteration
    response = agent.receive(message)
    match response:
        case Generator():
            yield from response
        case Message():
            yield response


def propogate(message: Message, applicator: Applicator = apply) -> Iterable[Message]:
    for reply in applicator(message):
        yield reply
        yield from propogate(reply)
