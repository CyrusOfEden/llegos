from typing import Iterable

from gpt_net.message import AssistantMessage, Message, UserMessage
from gpt_net.node import Field, Node
from gpt_net.openai import chat_message, chat_messages, node_fn


def test_fn_node_call():
    class Repeater(Node):
        """A node that repeats messages."""

        times: int = Field(default=1, gt=0)

        def chat(self, message: Message) -> Iterable[Message]:
            for _ in range(self.times):
                yield message

    assert node_fn(Repeater, [Message]) == {
        "name": "Repeater",
        "description": "A node that repeats messages.",
        "parameters": {
            "type": "object",
            "oneOf": [Message.schema()],
        },
    }


def test_chat_message():
    message = UserMessage(content="hello", from_id="pytest", type="chat")
    assert chat_message(message) == {"role": "user", "content": "hello"}


def test_chat_messages():
    messages = [
        UserMessage(content="hello", from_id="user", type="chat"),
        AssistantMessage(content="hi", from_id="assistant", type="chat"),
    ]

    assert list(chat_messages(messages)) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
