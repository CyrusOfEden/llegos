from typing import Literal

from pydantic import BaseModel


class FunctionCallCompletion(BaseModel):
    content: dict[Literal["function_call"], dict[Literal["name", "arguments"], str]]


class MockCompletion(BaseModel):
    choices: list[FunctionCallCompletion]
