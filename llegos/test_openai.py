from typing import Literal, Optional

import pytest
from pydantic import BaseModel

from llegos.asyncio import AsyncAgent, EphemeralMessage
from llegos.openai import callable_schemas, parse_function_call, prepare_async_call
from llegos.test_helpers import MockAsyncAgent


class FunctionCallCompletion(BaseModel):
    content: dict[Literal["function_call"], dict[Literal["name", "arguments"], str]]


class MockCompletion(BaseModel):
    choices: list[FunctionCallCompletion]


class TestCallableSchemas:
    def test_callable_schemas(self):
        llegos = [MockAsyncAgent(), EphemeralMessage]
        callables, schemas = callable_schemas(llegos)

        assert len(callables) == 2
        assert len(schemas) == 2

        for schema in schemas:
            assert "name" in schema
            assert "parameters" in schema
            assert "required" in schema

        for llego in llegos:
            match llego:
                case MockAsyncAgent():
                    key = str(llego.id)
                    assert key in callables
                    assert callables[key][0] == "receive"
                    assert callables[key][1] == llego.receive
                case type():
                    key = llego.__name__
                    assert key in callables
                    assert callables[key][0] == "init"
                    assert callables[key][1] == llego


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
            AsyncAgent(),
            EphemeralMessage,
        ]
        schemas, function_call = prepare_async_call(llegos)
        assert len(schemas) == 2
        assert schemas[0]["name"] == str(llegos[0].id)
        assert schemas[1]["name"] == "EphemeralMessage"

        completion = MockCompletion.parse_obj(
            {
                "choices": [
                    {
                        "content": {
                            "function_call": {
                                "name": "EphemeralMessage",
                                "arguments": '{ "intent": "chat", "body": "Hello" }',
                            }
                        }
                    }
                ]
            }
        )

        message: Optional[EphemeralMessage] = None
        async for result in function_call(completion):
            message = result

        assert message
        assert message.intent == "chat"
        assert message.body == "Hello"

    @pytest.mark.asyncio
    async def test_receive_message(self):
        llegos = [
            MockAsyncAgent(),
            MockAsyncAgent(),
            EphemeralMessage,
        ]
        schemas, async_function_call = prepare_async_call(llegos)

        completion = MockCompletion.parse_obj(
            {
                "choices": [
                    {
                        "content": {
                            "function_call": {
                                "name": str(llegos[1].id),
                                "arguments": '{ "intent": "inform", "body": "Hello" }',
                            }
                        }
                    }
                ]
            }
        )

        results: list[EphemeralMessage] = []
        async for message in async_function_call(completion):
            results.append(message)

        assert len(results) == 1

        ack = results[0]

        assert ack
        assert ack.intent == "ack"
        assert ack.body.startswith("Ack: ")

    @pytest.mark.asyncio
    async def test_unknown_completion_call(self):
        llegos = [
            MockAsyncAgent(),
            MockAsyncAgent(),
            EphemeralMessage,
        ]
        schemas, async_function_call = prepare_async_call(llegos)
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
            async for reply in async_function_call(completion):
                ...
