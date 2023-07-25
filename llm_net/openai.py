import json
from typing import AsyncIterable, Iterable, Optional, Tuple, TypeVar

from openai import ChatCompletion
from pydantic import BaseModel, Field

from llm_net.asyncio import AsyncGenAgent
from llm_net.base import GenAgent, Message


def chat_message(message: Message) -> Message:
    return {"role": message.role, "content": str(message)}


def chat_messages(messages: Iterable[Message]) -> Iterable[Message]:
    return map(chat_message, messages)


class OpenAIAgent(GenAgent):
    completion: ChatCompletion = Field()


def model_fn(model: type[BaseModel]):
    return {
        "name": model.__name__,
        "description": model.__doc__,
        "parameters": model.schema()["properties"],
    }


generic_message_fn = model_fn(Message)


def agent_fn(agent: GenAgent):
    return {
        "name": agent.id,
        "description": agent.description,
        "parameters": {
            "type": "object",
            "oneOf": [
                message_class.schema() for message_class in agent.receivable_messages
            ],
        },
    }


def parse_completion_kwargs(completion) -> dict:
    message = completion.choices[0].message
    return json.loads(message["function_call"]["arguments"])


def parse_completion_fn_call(
    completion, fn_name: Optional[str] = None, throw_error=True
) -> Tuple[str, dict]:
    response = completion.choices[0].content

    if throw_error:
        assert "function_call" in response
        if fn_name is not None:
            assert response["function_call"]["name"] == fn_name

    name = response["function_call"]["name"]

    return (name, parse_completion_kwargs(completion))


T = TypeVar("T")


def parse_model(model: type[T], completion) -> T:
    return model(**parse_completion_kwargs(completion))


def call_agent_fn(completion, node: GenAgent, throw_error=True) -> Iterable[Message]:
    kwargs = parse_completion_fn_call(completion, node.__name__, throw_error)
    yield from node.receive(**kwargs)


async def acall_agent_fn(
    completion, node: AsyncGenAgent, throw_error=True
) -> AsyncIterable[Message]:
    kwargs = parse_completion_fn_call(completion, node.__name__, throw_error)
    return node.areceive(**kwargs)
