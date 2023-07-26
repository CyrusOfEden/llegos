import json
from typing import Iterable, Union

from gen_net.llegos.messages import messages_iter
from gen_net.llegos.sync import AbstractObject, GenAgent, Message

Llego = Union[GenAgent, AbstractObject]


def messages_dicts(message: Message, count: int = 12):
    return [
        {"role": message.role, "content": str(message)}
        for message in messages_iter(message, count=count)
    ]


def schemas_and_callables(llegos: Iterable[Llego]):
    schemas = []
    callables = {}
    for llego in llegos:
        if isinstance(llego, GenAgent):
            schema = llego.receive_fn
            schemas.append(schema)
            callables[schema["name"]] = ("receive", llego.receive)
        else:
            schema = llego.init_schema
            schemas.append(schema)
            callables[schema["name"]] = ("init", llego)
    return schemas, callables


def prepare_function_call(llegos: Iterable[Llego]):
    schemas, callables = schemas_and_callables(llegos)

    def coroutine_call(completion):
        response = completion.choices[0].content["function_call"]
        if "function_call" not in response:
            raise StopIteration

        response = response["function_call"]
        method, callable = callables[response["name"]]
        kwargs = json.loads(response["arguments"])
        match method:
            case "receive":
                yield from callable(Message(**kwargs))
            case "init":
                yield callable(**kwargs)

    return schemas, coroutine_call


def prepare_async_function_call(llegos: Iterable[Llego]):
    schemas, callables = schemas_and_callables(llegos)

    async def coroutine_call(completion):
        response = completion.choices[0].content["function_call"]
        if "function_call" not in response:
            raise StopAsyncIteration

        response = response["function_call"]
        method, callable = callables[response["name"]]
        kwargs = json.loads(response["arguments"])
        match method:
            case "receive":
                async for reply in callable(Message(**kwargs)):
                    yield reply
            case "init":
                yield callable(**kwargs)

    return schemas, coroutine_call
