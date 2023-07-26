from typing import Iterable

from gen_net.agents import Field, GenAgent
from gen_net.messages import Message
from gen_net.openai import chat_message, chat_messages


def test_fn_node_call():
    class Repeater(GenAgent):
        """A node that repeats messages."""

        times: int = Field(default=1, gt=0)

        def chat(self, message: Message) -> Iterable[Message]:
            for _ in range(self.times):
                yield message

    assert agent_fn(Repeater, [Message]) == {
        "name": "Repeater",
        "description": "A node that repeats messages.",
        "parameters": {
            "type": "object",
            "oneOf": [Message.schema()],
        },
    }


def test_chat_message():
    message = UserMessage(content="hello", sender="pytest", method="chat")
    assert chat_message(message) == {"role": "user", "content": "hello"}


def test_chat_messages():
    messages = [
        UserMessage(content="hello", sender="user", method="chat"),
        AssistantMessage(content="hi", sender="assistant", method="chat"),
    ]

    assert list(chat_messages(messages)) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
