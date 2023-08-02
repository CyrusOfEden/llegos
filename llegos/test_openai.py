from typing import Literal

import pytest
from pydantic import BaseModel

from llegos.asyncio import AsyncAgent
from llegos.messages import Ack
from llegos.openai import callable_schemas, parse_function_call, prepare_functions
from llegos.test_helpers import ChatMessage, EphemeralMessage, MockAsyncAgent


class FunctionCallCompletion(BaseModel):
    content: dict[Literal["function_call"], dict[Literal["name", "arguments"], str]]


class MockCompletion(BaseModel):
    choices: list[FunctionCallCompletion]


class TestCallableSchemas:
    def test_function_schemas(self):
        llegos = [MockAsyncAgent(), EphemeralMessage]
        callables, schemas = callable_schemas(llegos)

        assert len(callables) == 2
        assert len(schemas) == 2

        for schema in schemas:
            assert "name" in schema
            assert "parameters" in schema
            assert "required" in schema

        for llego in llegos:
            key = str(llego.id) if isinstance(llego, AsyncAgent) else llego.__name__
            assert key in callables
            assert callables[key] == llego


class TestParseFunctionCall:
    def test_valid_completion_object(self):
        completion = MockCompletion.parse_obj(
            {
                "choices": [
                    {
                        "content": {
                            "function_call": {
                                "name": "function_name",
                                "arguments": '{"arg1": 1, "arg2": 2}',
                            }
                        }
                    }
                ]
            }
        )
        expected_name = "function_name"
        expected_arguments = {"arg1": 1, "arg2": 2}
        name, arguments = parse_function_call(completion)
        assert name == expected_name
        assert arguments == expected_arguments


class TestPrepareAsyncCall:
    @pytest.mark.asyncio
    async def test_create_message(self):
        llegos = [
            MockAsyncAgent(),
            ChatMessage,
        ]
        schemas, function_call = prepare_functions(llegos)
        assert len(schemas) == 2
        assert schemas[0]["name"] == str(llegos[0].id)
        assert schemas[1]["name"] == "ChatMessage"

        completion = MockCompletion.parse_obj(
            {
                "choices": [
                    {
                        "content": {
                            "function_call": {
                                "name": "ChatMessage",
                                "arguments": '{ "body": "Hello" }',
                            }
                        }
                    }
                ]
            }
        )

        message: ChatMessage = function_call(completion)

        assert message
        assert message.intent == "chat_message"
        assert message.body == "Hello"

    @pytest.mark.asyncio
    async def test_receive_message(self):
        llegos = [
            MockAsyncAgent(),
            MockAsyncAgent(),
            ChatMessage,
        ]
        schemas, function_call = prepare_functions(llegos)

        completion = MockCompletion.parse_obj(
            {
                "choices": [
                    {
                        "content": {
                            "function_call": {
                                "name": str(llegos[1].id),
                                "arguments": '{ "intent": "ack" }',
                            }
                        }
                    }
                ]
            }
        )

        ack: EphemeralMessage = await anext(function_call(completion))

        assert ack
        assert ack.intent == "ack"
        assert ack.parent is not None  # the message sent by the function call

    @pytest.mark.asyncio
    async def test_unknown_completion_call(self):
        llegos = [
            MockAsyncAgent(),
            MockAsyncAgent(),
            Ack,
        ]
        schemas, function_call = prepare_functions(llegos)
        completion = MockCompletion.parse_obj(
            {
                "choices": [
                    {
                        "content": {
                            "function_call": {
                                "name": "unknown_function",
                                "arguments": '{ "intent": "chat", "body": "Hello" }',
                            }
                        }
                    }
                ]
            }
        )
        with pytest.raises(KeyError):
            function_call(completion)
            function_call(completion)
