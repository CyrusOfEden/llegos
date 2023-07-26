from typing import Literal, Union

Role = Union[str, Literal["system", "user", "assistant"]]
Method = Literal[
    "ask",
    "be",
    "chat",
    "do",
    "error",
    "info",
    "inform",
    "log",
    "proxy",
    "query",
    "request",
    "response",
    "step",
    "system",
    "warn",
]
