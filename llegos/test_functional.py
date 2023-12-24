import typing as t

from pydantic import Field

from .functional import model_tool
from .research import Message, Object


def test_simple_message() -> None:
    """Model tools should not pollute the schema with irrelevant properties"""

    class Text(Message):
        "A simple text message"
        text: str

    schema = model_tool(Text)
    assert schema["function"]["name"] == Text.__name__
    assert schema["function"]["description"] == Text.__doc__

    params: dict[str, t.Any] = schema["function"]["parameters"]
    assert params["required"] == ["text"]
    assert set(params["properties"].keys()) == {"metadata", "text"}


def test_complex_message() -> None:
    """Model tools should respect non-internal $defs"""

    class Task(Object):
        action: str
        deps: list[str] = Field(
            description="A list of task ids that must be completed first"
        )

    class Plan(Message):
        "Plan a series of tasks"
        tasks: list[Task]

    schema = model_tool(Plan)
    assert schema["function"]["name"] == Plan.__name__
    assert schema["function"]["description"] == Plan.__doc__

    params: dict[str, t.Any] = schema["function"]["parameters"]
    assert params["required"] == ["tasks"]
    assert set(params["properties"].keys()) == {"metadata", "tasks"}
    assert set(params["properties"].keys()) == {"metadata", "tasks"}
