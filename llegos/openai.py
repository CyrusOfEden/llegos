import json
from textwrap import dedent
from typing import Callable, Iterable

from openai import ChatCompletion
from openai.openai_object import OpenAIObject
from pydantic import UUID4

from llegos.ephemeral import EphemeralAgent, EphemeralCognition, EphemeralMessage
from llegos.messages import Chat, message_chain


class OpenAICognition(EphemeralCognition):
    language: ChatCompletion


def function_schema(exclude_keys={"title"}, **schema):
    for key, value in list(schema.items()):
        if key in exclude_keys:
            del schema[key]
        elif isinstance(value, dict):
            schema[key] = function_schema(exclude_keys=exclude_keys, **value)
    return schema


def message_schema(
    cls: type[EphemeralMessage],
    remove_keys: set[str] = {
        "id",
        "created_at",
        "sender",
        "receiver",
        "parent",
        "context",
    },
):
    schema = cls.schema()
    intent = cls.infer_intent()

    params = schema["properties"]
    params["intent"]["enum"] = [intent]
    for key in remove_keys:
        params.pop(key, None)

    reqs = schema.get("required", [])

    defs = schema.get("definitions", {})
    defs.pop("EphemeralMessage", None)
    defs.pop("EphemeralObject", None)

    return function_schema(
        name=intent,
        description=cls.__doc__,
        parameters={
            "type": "object",
            "properties": params,
        },
        required=reqs,
        definitions=defs,
    )


def receive_schema(agent: EphemeralAgent, messages: set[type[EphemeralMessage]] = None):
    defs = []

    for m in agent.receivable_messages:
        if messages and m not in messages:
            continue
        schema = message_schema(m)
        schema.update(schema.pop("parameters"))  # since it is being nested
        # defs.update(schema.pop("definitions", {}))
        defs.append(schema)
        # refs.append({"$ref": f"#/definitions/{clsname}"})

    return function_schema(
        name=str(agent.id),
        description=agent.description,
        parameters={
            "type": "object",
            "properties": {"message": {"oneOf": defs}},
        },
        required=["message"],
    )


def standard_context_transformer(messages: Iterable[EphemeralMessage]) -> list[dict]:
    return [{"content": str(message), "role": "user"} for message in messages]


def use_messages(
    system: str,
    prompt: str,
    context: EphemeralMessage | None = None,
    context_history: int = 8,
    context_transformer: Callable[
        [Iterable[EphemeralMessage]], list[dict]
    ] = standard_context_transformer,
):
    return [
        {"content": dedent(system), "role": "system"},
        *context_transformer(message_chain(context, height=context_history)),
        {"content": dedent(prompt), "role": "user"},
    ]


def use_write_message(messages: Iterable[type[EphemeralMessage]], **kwargs):
    schemas = []
    message_lookup = {}

    for cls in messages:
        schema: dict = message_schema(cls)
        schemas.append(schema)
        message_lookup[schema["name"]] = cls

    def function_call(completion: OpenAIObject):
        response = completion.choices[0].message
        if call := response.get("function_call", None):
            cls = message_lookup[call.name]
            genargs = json.loads(call.arguments)
            genargs.update(kwargs)

            yield cls(**genargs)
        if content := response.get("content", None):
            yield Chat(**kwargs, message=content)

    create_kwargs = {
        "functions": schemas,
    }

    return create_kwargs, function_call


def use_agent_message(
    messages: set[type[EphemeralMessage]],
    agents: Iterable[EphemeralAgent],
    **kwargs,
):
    schemas = []
    agent_lookup: dict[UUID4, EphemeralAgent] = {}
    message_lookup: dict[str, EphemeralMessage] = {}

    for agent in agents:
        schema: dict = receive_schema(agent, messages=messages)
        schemas.append(schema)
        agent_lookup[schema["name"]] = agent

        for cls in agent.receivable_messages:
            if (intent := cls.infer_intent()) and intent not in message_lookup:
                message_lookup[intent] = cls

    def function_call(completion: OpenAIObject):
        response = completion.choices[0].message
        if call := response.get("function_call", None):
            agent = agent_lookup[call.name]
            raw = json.loads(call.arguments)
            genargs = raw.pop("message", raw)
            cls = message_lookup[genargs.pop("intent")]
            yield cls(**genargs, **kwargs, receiver=agent)
        if content := response.get("content", None):
            yield Chat(**kwargs, message=content)

    create_kwargs = {
        "functions": schemas,
    }

    return create_kwargs, function_call
