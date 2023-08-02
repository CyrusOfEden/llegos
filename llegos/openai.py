import json

from beartype import beartype
from beartype.typing import Iterable
from openai import ChatCompletion
from openai.openai_object import OpenAIObject
from pydantic import BaseModel

from llegos.asyncio import AsyncAgent
from llegos.ephemeral import EphemeralAgent, EphemeralMessage, EphemeralObject, Field
from llegos.messages import SystemMessage, message_chain


class OpenAIAgent(AsyncAgent):
    completion: ChatCompletion = Field()


def message_dict(message: EphemeralMessage):
    return {"role": message.role, "content": str(message)}


def message_dicts(message: EphemeralMessage, history: int = 12):
    return [message_dict(m) for m in message_chain(message, height=history)]


@beartype
def schema_init(cls: type[BaseModel]):
    schema = cls.schema()
    if "properties" not in schema:
        schema = schema["definitions"][cls.__name__]

    parameters = {}
    for key, value in schema["properties"].items():
        if key == "id":
            continue
        elif value.get("serialization_alias", "").endswith("_id"):
            parameters[f"{key}_id"] = {
                "title": value["title"],
                "type": "string",
            }
        else:
            parameters[key] = value

    return {
        "name": cls.__name__,
        "description": cls.__doc__,
        "parameters": parameters,
        "required": schema.get("required", []),
    }


@beartype
def schema_receive(agent: EphemeralAgent):
    return {
        "name": str(agent.id),
        "description": agent.public_description,
        "parameters": {
            "message": {"oneOf": map(schema_init, agent.receivable_messages)},
        },
        "required": ["message"],
    }


@beartype
def callable_schemas(
    llegos: Iterable[EphemeralAgent | AsyncAgent | type[EphemeralMessage]],
) -> tuple[dict[str, callable], list[dict]]:
    "Returns a lookup dictionary of callables and a list of schemas"
    schemas = []
    callables = {}
    for llego in llegos:
        schema = (
            schema_init(llego) if isinstance(llego, type) else schema_receive(llego)
        )
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
