import json
from typing import Iterable

from openai import ChatCompletion
from openai.openai_object import OpenAIObject

from llegos.asyncio import AsyncAgent
from llegos.ephemeral import EphemeralAgent, EphemeralMessage, EphemeralObject, Field
from llegos.messages import SystemMessage, message_chain


class OpenAIAgent(AsyncAgent):
    completion: ChatCompletion = Field()


def message_dict(message: EphemeralMessage):
    return {"role": message.role, "content": str(message)}


def message_dicts(message: EphemeralMessage, history: int = 12):
    return [message_dict(m) for m in message_chain(message, height=history)]


def callable_schemas(
    llegos: Iterable[EphemeralAgent | AsyncAgent | type[EphemeralMessage]],
) -> tuple[dict[str, tuple[str, callable]], list[dict]]:
    schemas = []
    callables = {}
    for llego in llegos:
        schema = llego.init_schema if isinstance(llego, type) else llego.call_schema
        schemas.append(schema)
        callables[schema["name"]] = llego
    return callables, schemas


def parse_function_call(completion: OpenAIObject):
    call = completion.choices[0].content["function_call"]
    return call["name"], json.loads(call["arguments"])


def prepare_messages(system: SystemMessage, prompt: EphemeralMessage):
    return [message_dict(system), *message_dicts(prompt)]


def prepare_functions(
    llegos: Iterable[EphemeralAgent | type[EphemeralMessage]],
):
    callables, schemas = callable_schemas(llegos)

    def function_call(completion: OpenAIObject):
        name, kwargs = parse_function_call(completion)
        callable = callables[name]

        if isinstance(callable, type) and issubclass(callable, EphemeralObject):
            init_object = callable
            return init_object(**kwargs)

        agent_receive = callable(EphemeralMessage(**kwargs))
        return agent_receive

    return schemas, function_call
