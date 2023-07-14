import json
from typing import AsyncIterable, Iterable, List, Optional, Union

from openai import ChatCompletion
from pydantic import Field

from gpt_net.async_node import AsyncNode
from gpt_net.node import AssistantNode, Message, Node


class OpenAINode(AsyncNode, AssistantNode):
    completion: ChatCompletion = Field()


def message_fn(message: Union[type[Message], Message]):
    message_class = message if isinstance(message, type) else message.__class__

    return {
        "name": message_class.__name__,
        "description": message_class.__doc__,
        "parameters": message_class.schema()["properties"],
    }


def node_fn(node: Union[type[Node], Node], message_types: List[type[Message]]):
    node_class = node if isinstance(node, type) else node.__class__

    return {
        "name": node_class.__name__,
        "description": node_class.__doc__,
        "parameters": {
            "type": "object",
            "oneOf": [message_type.schema() for message_type in message_types],
        },
    }


def parse_completion_fn_call(
    completion, fn_name: Optional[str] = None, throw_error=True
):
    message = completion.choices[0].message

    if throw_error:
        assert "function_call" in message
        assert message["function_call"]["name"] == fn_name

    return json.loads(message["function_call"]["arguments"])


def call_node_fn(completion, node: Node, throw_error=True) -> Iterable[Message]:
    kwargs = parse_completion_fn_call(completion, node.__name__, throw_error)
    yield from node.receive(**kwargs)


async def acall_node_fn(
    completion, node: AsyncNode, throw_error=True
) -> AsyncIterable[Message]:
    kwargs = parse_completion_fn_call(completion, node.__name__, throw_error)
    async for message in node.areceive(**kwargs):
        yield message


def chat_message(message: Message) -> Message:
    return {"role": message.role, "content": message.content}


def chat_messages(messages: Iterable[Message]) -> Iterable[Message]:
    return map(chat_message, messages)
