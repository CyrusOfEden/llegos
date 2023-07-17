import json
from typing import AsyncIterable, Iterable, List, Optional, Tuple

from openai import ChatCompletion
from pydantic import Field

from llm_net.abstract import AbstractObject
from llm_net.gen import AssistantAgent, GenAgent, Message
from llm_net.gen_async import GenAsyncAgent


class OpenAIAgent(GenAsyncAgent, AssistantAgent):
    completion: ChatCompletion = Field(default_factory=ChatCompletion)


def model_fn(model: type[AbstractObject]):
    return {
        "name": model.__name__,
        "description": model.__doc__,
        "parameters": model.schema()["properties"],
    }


message_fn = model_fn(Message)


def method_fns(methods: Iterable[str]) -> List[dict]:
    pass


response_fn = method_fns(["response"])[0]


def agent_fn(agent: GenAgent):
    return {
        "name": agent.id,
        "description": agent.description,
        "parameters": {
            "type": "object",
            "oneOf": [message_type.schema() for message_type in agent.methods],
        },
    }


def get_completion_message(completion) -> Message:
    return completion.choices[0].message


def parse_completion_fn_call(
    completion, fn_name: Optional[str] = None, throw_error=True
) -> Tuple[str, dict]:
    message = get_completion_message(completion)

    if throw_error:
        assert "function_call" in message
        if fn_name is not None:
            assert message["function_call"]["name"] == fn_name

    name = message["function_call"]["name"]
    params = json.loads(message["function_call"]["arguments"])

    return (name, params)


def call_agent_fn(completion, node: GenAgent, throw_error=True) -> Iterable[Message]:
    kwargs = parse_completion_fn_call(completion, node.__name__, throw_error)
    yield from node.receive(**kwargs)


async def acall_agent_fn(
    completion, node: GenAsyncAgent, throw_error=True
) -> AsyncIterable[Message]:
    kwargs = parse_completion_fn_call(completion, node.__name__, throw_error)
    async for message in node.areceive(**kwargs):
        yield message


def chat_message(message: Message) -> Message:
    return {"role": message.role, "content": str(message)}


def chat_messages(messages: Iterable[Message]) -> Iterable[Message]:
    return map(chat_message, messages)
