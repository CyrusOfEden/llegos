from typing import Iterable

from cursive.function import CursiveCustomFunction
from pydantic import UUID4

from llegos.research import Actor, Message, Object, message_chain


class maxdict(dict):
    def __init__(self, max_size=128, *args, **kwargs):
        self.max_size = max_size
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if len(self) == self.max_size:
            oldest = next(iter(self))
            del self[oldest]
        super().__setitem__(key, value)


actor_lookup = maxdict[UUID4, Actor](max_size=128)
message_lookup = dict[UUID4, type[Message]]()


def hydrate_message(m: Message) -> Message:
    match m.parent:
        case Message() as m:
            message_lookup[m.id] = m
        case Object() as o:
            m.parent = message_lookup[o.id]

    match m.sender:
        case Actor() as a:
            actor_lookup[a.id] = a
        case Object() as o:
            m.sender = actor_lookup[o.id]

    match m.receiver:
        case Actor() as a:
            actor_lookup[a.id] = a
        case Object() as o:
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


def use_messages(
    context_history: int,
    context: Message,
):
    return (to_openai_json(message_chain(context, height=context_history)),)


def use_gen_message_fn(cls: type[Message], **kwargs):
    global message_lookup
    message_lookup[cls.infer_intent()] = cls

    json_schema: dict = message_schema(cls)
    return CursiveCustomFunction(
        definition=lambda **genargs: hydrate_message(cls(**kwargs, **genargs)),
        function_schema=json_schema,
        pause=True,
    )


def use_gen_message_fns(messages: Iterable[type[Message]], **kwargs):
    return [use_gen_message_fn(cls, **kwargs) for cls in messages]


def use_actor_message_fn(actor: Actor, messages: set[type[Message]], **kwargs):
    global actor_lookup
    global message_lookup

    actor_lookup[actor.id] = actor
    for cls in actor.receivable_messages:
        message_lookup[cls.infer_intent()] = cls

    def actor_message(**genargs):
        cls = message_lookup[genargs["intent"]]
        message = cls(**kwargs, **genargs)
        return hydrate_message(message)

    json_schema: dict = receive_schema(actor, messages=messages)

    return CursiveCustomFunction(
        definition=actor_message, function_schema=json_schema, pause=True
    )


def use_actor_message_fns(
    actors: Iterable[Actor],
    messages: set[type[Message]],
    **kwargs,
):
    return [use_actor_message_fn(actor, messages, **kwargs) for actor in actors]


def use_reply_to_fn(m: Message, ms: set[type[Message]], **kwargs):
    if not m.sender_id:
        raise ValueError("message must have a sender to generate a reply")

    return use_actor_message_fn(
        m.sender, ms, parent=m, sender=m.receiver, receiver=m.sender, **kwargs
    )


def use_reply_to_fns(m: Message, ms: set[type[Message]], **kwargs):
    return [use_reply_to_fn(m, ms, **kwargs) for m in m.sender.received_messages]
