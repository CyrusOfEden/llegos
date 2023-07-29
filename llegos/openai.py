import json
from typing import Iterable

from llegos.asyncio import AsyncAgent
from llegos.ephemeral import EphemeralAgent, EphemeralMessage
from llegos.messages import message_chain


def message_dicts(message: EphemeralMessage, history: int = 12):
    return [
        {"role": message.role, "content": str(message)}
        for message in message_chain(message, height=history)
    ]


def callable_schemas(
    llegos: Iterable[EphemeralAgent | AsyncAgent | type[EphemeralMessage]],
) -> tuple[dict[str, tuple[str, callable]], list[dict]]:
    schemas = []
    callables = {}
    for llego in llegos:
        if isinstance(llego, EphemeralAgent):
            schema = llego.receive_schema
            schemas.append(schema)
            callables[schema["name"]] = ("receive", llego.receive)
        else:
            schema = llego.init_schema
            schemas.append(schema)
            callables[schema["name"]] = ("init", llego)
    return callables, schemas


def parse_function_call(completion):
    call = completion.choices[0].content["function_call"]
    return call["name"], json.loads(call["arguments"])


def prepare_call(llegos: Iterable[EphemeralAgent | type[EphemeralMessage]]):
    callables, schemas = callable_schemas(llegos)

    def function_call(completion):
        name, kwargs = parse_function_call(completion)
        method, callable = callables[name]
        match method:
            case "receive":
                yield from callable(EphemeralMessage(**kwargs))
            case "init":
                yield callable(**kwargs)

    return schemas, function_call


def prepare_async_call(llegos: Iterable[AsyncAgent | type[EphemeralMessage]]):
    callables, schemas = callable_schemas(llegos)

    async def async_function_call(completion):
        name, kwargs = parse_function_call(completion)
        method, callable = callables[name]
        match method:
            case "receive":
                async for reply in callable(EphemeralMessage(**kwargs)):
                    yield reply
            case "init":
                yield callable(**kwargs)

    return schemas, async_function_call
