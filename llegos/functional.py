import json
from textwrap import dedent
from typing import Iterable

from openai.openai_object import OpenAIObject
from pydantic import UUID4

from llegos.research import Actor, Message, SceneObject, message_chain


class maxdict(dict):
    def __init__(self, max_size=100, *args, **kwargs):
        self.max_size = max_size
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if len(self) == self.max_size:
            oldest = next(iter(self))
            del self[oldest]
        super().__setitem__(key, value)


actor_lookup: dict[UUID4, Actor] = {}
message_lookup: maxdict[UUID4, Message] = maxdict(max_size=1024)


def hydrate_message(m: Message) -> Message:
    match m.parent:
        case Message() as m:
            message_lookup[m.id] = m
        case SceneObject() as o:
            m.parent = message_lookup[o.id]

    match m.sender:
        case Actor() as a:
            actor_lookup[a.id] = a
        case SceneObject() as o:
            m.sender = actor_lookup[o.id]

    match m.receiver:
        case Actor() as a:
            actor_lookup[a.id] = a
        case SceneObject() as o:
            m.receiver = actor_lookup[o.id]

    return m


def compact_schema(exclude_keys={"title"}, **schema):
    for key, value in list(schema.items()):
        if key in exclude_keys:
            del schema[key]
        elif isinstance(value, dict):
            schema[key] = compact_schema(exclude_keys, **value)
    return schema


def message_schema(
    cls: type[Message],
    delete_keys: set[str] = {
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
    for key in delete_keys:
        params.pop(key, None)

    reqs = schema.get("required", [])

    defs = schema.get("definitions", {})
    defs.pop(Message, None)
    defs.pop("SceneObject", None)

    return compact_schema(
        name=intent,
        description=cls.__doc__,
        parameters={
            "type": "object",
            "properties": params,
        },
        required=reqs,
        definitions=defs,
    )


def receive_schema(agent: Actor, messages: set[type[Message]] = None):
    defs = []

    for m in agent.receivable_messages:
        if messages and m not in messages:
            continue
        schema = message_schema(m)
        schema.update(schema.pop("parameters"))  # since it is being nested
        # defs.update(schema.pop("definitions", {}))
        defs.append(schema)
        # refs.append({"$ref": f"#/definitions/{clsname}"})

    return compact_schema(
        name=str(agent.id),
        description=agent.system,
        parameters={
            "type": "object",
            "properties": {"message": {"oneOf": defs}},
        },
        required=["message"],
    )


def to_openai_json(messages: Iterable[Message]) -> list[dict]:
    return [{"content": str(message), "role": "user"} for message in messages]


def use_model(
    system: str,
    prompt: str,
    context: Message | None = None,
    context_history: int = 8,
    **kwargs,
):
    kwargs["messages"] = [
        {"content": dedent(system), "role": "system"},
        *to_openai_json(message_chain(context, height=context_history)),
        {"content": dedent(prompt), "role": "user"},
    ]
    return kwargs


def use_gen_message(messages: Iterable[type[Message]], **kwargs):
    schemas = []
    message_lookup = {}

    for cls in messages:
        schema: dict = message_schema(cls)
        schemas.append(schema)
        message_lookup[schema["name"]] = cls

    create_kwargs = {"functions": schemas}

    def function_call(completion: OpenAIObject):
        response = completion.choices[0].message
        if call := response.get("function_call", None):
            cls = message_lookup[call.name]
            genargs = json.loads(call.arguments)
            genargs.update(kwargs)
            return hydrate_message(cls(**genargs))
        if content := response.get("content", None):
            try:
                call = json.loads(content)["function_call"]
                genargs = call["args"]["message"]
                genargs.update(kwargs)
                cls = message_lookup[genargs["intent"]]
                return hydrate_message(cls(**genargs))
            except json.JSONDecodeError or KeyError:
                return hydrate_message(Message(**kwargs, content=content))

    return create_kwargs, function_call


def use_actor_message(
    actors: Iterable[Actor],
    messages: set[type[Message]],
    **kwargs,
):
    global actor_lookup

    schemas = []
    message_lookup: dict[str, Message] = {}

    for actor in actors:
        schema: dict = receive_schema(actor, messages=messages)
        schemas.append(schema)
        actor_lookup[schema["name"]] = actor

        for cls in actor.receivable_messages:
            if (intent := cls.infer_intent()) and intent not in message_lookup:
                message_lookup[intent] = cls

    create_kwargs = {"functions": schemas}

    def function_call(completion: OpenAIObject):
        response = completion.choices[0].message
        if call := response.get("function_call", None):
            raw = json.loads(call.arguments)
            genargs = raw.pop("message", raw)
            genargs.update(kwargs)

            agent = actor_lookup[call.name]
            genargs["receiver"] = agent

            cls = message_lookup[genargs.pop("intent")]
            return hydrate_message(cls(**genargs))
        if content := response.get("content", None):
            return hydrate_message(Message(**kwargs, content=content))

    return create_kwargs, function_call


def use_reply_to(m: Message, ms: set[type[Message]], **kwargs):
    if not m.sender_id:
        raise ValueError("message must have a sender to generate a reply")

    return use_actor_message(
        [m.sender], ms, parent=m, sender=m.receiver, receiver=m.sender, **kwargs
    )
