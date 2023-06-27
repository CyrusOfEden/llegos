import json
from typing import Any, Callable, Dict, List, Set

from pydantic import BaseModel, validate_arguments

from llambdao.message import Message
from llambdao.node.asyncio import AsyncNode


def deep_exclude(d: Dict[str, Any], keys: Set[str]):
    if not isinstance(d, dict):
        return d
    return {k: deep_exclude(v, keys) for (k, v) in d.items() if k not in keys}


def data_model(model: BaseModel):
    pass


EXCLUDED_ARGS = (
    "v__duplicate_kwargs",
    "args",
    "kwargs",
    "title",
    "additionalProperties",
)


def node_function(node: Callable):
    params = validate_arguments(node).model.schema()
    params["properties"] = {
        k: v for (k, v) in params["properties"].items() if k not in EXCLUDED_ARGS
    }
    params["required"] = sorted(params["properties"])
    return dict(name=node.__name__, description=node.__doc__, parameters=params)


def function_call(completion, function: Callable, throw_error=True):
    """TODO: How do we get OpenAI to create Messages?"""
    message = completion.choices[0].message

    if throw_error:
        assert "function_call" in message
        assert message["function_call"]["name"] == function.__name__

    call = message["function_call"]
    kwargs = json.loads(call["arguments"])
    return function(**kwargs)


async def async_node_function(node: AsyncNode):
    """TODO:"""
    pass


def chat_message(message: Message) -> Message:
    return {"role": message.role, "content": message.content}


def chat_messages(messages: List[Message]) -> List[Message]:
    return [chat_message(message) for message in messages]


def test_chat_message():
    message = Message(role="user", content="hello")
    assert chat_message(message) == {"role": "user", "content": "hello"}


def test_chat_messages():
    messages = [
        Message(role="user", content="hello"),
        Message(role="bot", content="hi"),
    ]

    assert chat_messages(messages) == [
        {"role": "user", "content": "hello"},
        {"role": "bot", "content": "hi"},
    ]
