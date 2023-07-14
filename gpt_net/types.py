from typing import Any, Dict, Literal, Union

Metadata = Dict[Any, Any]
Role = Union[str, Literal["system", "user", "assistant"]]
MessageTypes = Literal[
    "be",
    "chat",
    "do",
    "inform",
    "proxy",
    "query",
    "request",
    "response",
    "step",
    "system",
]
