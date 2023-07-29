import json
from typing import Iterable, Union

from llegos.asyncio import AsyncAgent
from llegos.ephemeral import EphemeralAgent, EphemeralMessage, message_chain


def message_dicts(message: EphemeralMessage, count: int = 12):
    return [
        {"role": message.role, "content": str(message)}
        for message in message_chain(message, count=count)
    ]


def callable_schemas(
    llegos: Iterable[Union[EphemeralAgent, AsyncAgent, type[EphemeralMessage]]]
):
    schemas = []
    callables = {}
    for llego in llegos:
        if isinstance(llego, EphemeralAgent):
            schema = llego.receive_fn
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


def prepare_call(llegos: Iterable[Union[EphemeralAgent, type[EphemeralMessage]]]):
    callables, schemas = callable_schemas(llegos)

    def coroutine_call(completion):
        name, kwargs = parse_function_call(completion)
        method, callable = callables[name]
        match method:
            case "receive":
                yield from callable(EphemeralMessage(**kwargs))
            case "init":
                yield callable(**kwargs)

    return schemas, coroutine_call


def prepare_async_call(llegos: Iterable[Union[AsyncAgent, type[EphemeralMessage]]]):
    callables, schemas = callable_schemas(llegos)

    async def coroutine_call(completion):
        name, kwargs = parse_function_call(completion)
        method, callable = callables[name]
        match method:
            case "receive":
                async for reply in callable(EphemeralMessage(**kwargs)):
                    yield reply
            case "init":
                yield callable(**kwargs)

    return schemas, coroutine_call
