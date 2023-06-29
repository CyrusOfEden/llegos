import json
from typing import Iterable, List, Union

from pydantic import Field

from llambdao.message import Message
from llambdao.sync import Node


def fn_build_message(message: Union[type[Message], Message]):
    message_class = message if isinstance(message, type) else message.__class__

    return {
        "name": message_class.__name__,
        "description": message_class.__doc__,
        "parameters": message_class.schema()["properties"],
    }


def fn_node_call(node: Union[type[Node], Node], message_types: List[type[Message]]):
    node_class = node if isinstance(node, type) else node.__class__

    return {
        "name": node_class.__name__,
        "description": node_class.__doc__,
        "parameters": {
            "type": "object",
            "oneOf": [message_type.schema() for message_type in message_types],
        },
    }


def test_fn_node_call():
    class Repeater(Node):
        """A node that repeats messages."""

        times: int = Field(default=1, gt=0)

        def chat(self, message: Message) -> Iterable[Message]:
            for _ in range(self.times):
                yield message

    assert fn_node_call(Repeater, [Message]) == {
        "name": "Repeater",
        "description": "A node that repeats messages.",
        "parameters": {
            "type": "object",
            "oneOf": [Message.schema()],
        },
    }


def completion_node_call(completion, node: Node, throw_error=True) -> Iterable[Message]:
    message = completion.choices[0].message

    if throw_error:
        assert "function_call" in message
        assert message["function_call"]["name"] == node.__name__

    call = message["function_call"]
    kwargs = json.loads(call["arguments"])
    yield from node.receive(**kwargs)


def chat_message(message: Message) -> Message:
    return {"role": message.role, "content": message.content}


def test_chat_message():
    message = Message(role="user", content="hello")
    assert chat_message(message) == {"role": "user", "content": "hello"}


def chat_messages(messages: Iterable[Message]) -> Iterable[Message]:
    return map(chat_message, messages)


def test_chat_messages():
    messages = [
        Message(role="user", content="hello"),
        Message(role="bot", content="hi"),
    ]

    assert list(chat_messages(messages)) == [
        {"role": "user", "content": "hello"},
        {"role": "bot", "content": "hi"},
    ]
