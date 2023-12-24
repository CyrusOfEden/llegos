import typing as t
from copy import deepcopy

from openai.types.chat import (
    ChatCompletion,
    ChatCompletionNamedToolChoiceParam,
    ChatCompletionToolParam,
)
from pydantic import BaseModel


def _clean_schema(schema: dict) -> dict:
    """
    Mutates the schema to remove irrelevant properties
    """
    schema.pop("additionalProperties", None)
    schema["properties"].pop("id")
    for prop in ["role", "created_at", "sender", "receiver", "parent"]:
        schema["properties"].pop(prop, None)
    schema["required"] = [
        p for p in schema["required"] if p not in {"sender", "receiver"}
    ]
    return schema


def model_tool(model: type[BaseModel]) -> ChatCompletionToolParam:
    tool: ChatCompletionToolParam = {
        "type": "function",
        "function": {
            "name": model.__name__,
            "parameters": deepcopy(model.model_json_schema()),
        },
    }

    schema: dict[str, t.Any] = tool["function"]["parameters"]
    if description := model.__doc__:
        tool["function"]["description"] = description

    _clean_schema(schema)
    for llegos_model in ["Object", "Actor", "Message"]:
        schema.get("$defs", {}).pop(llegos_model, None)
    for schema_def in schema.get("$defs", {}).values():
        _clean_schema(schema_def)

    tool["function"]["parameters"] = schema
    return tool


def model_tools(*models: type[BaseModel]) -> list[ChatCompletionToolParam]:
    return [model_tool(model) for model in models]


def choose_model_tool(model: type[BaseModel]) -> ChatCompletionNamedToolChoiceParam:
    return {"type": "function", "function": {"name": model.__name__}}


class ResponseModel(t.TypedDict):
    tools: list[ChatCompletionToolParam]
    tool_choice: ChatCompletionNamedToolChoiceParam


def response_model(model: type[BaseModel]) -> ResponseModel:
    return {
        "tools": model_tools(model),
        "tool_choice": choose_model_tool(model),
    }


class MissingToolCall(ValueError):
    ...


def parse_model(completion: ChatCompletion, model: type[BaseModel]) -> BaseModel:
    if tool_calls := completion.choices[0].message.tool_calls:
        return model.model_validate_json(tool_calls[0].function.arguments)
    raise MissingToolCall(completion)


def parse_models(
    completion: ChatCompletion, *models: type[BaseModel]
) -> list[BaseModel]:
    if tool_calls := completion.choices[0].message.tool_calls:
        lookup = {model.__name__: model for model in models}
        return [
            parse_model(completion, lookup[call.function.name])
            for call in tool_calls
            if call.function.name in lookup
        ]
    raise MissingToolCall(completion)
