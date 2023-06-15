from pprint import pprint
from typing import Iterable, Optional

from llambdao.abc import Node, StableChat
from llambdao.message import Message


def message_sequence(message: Message, limit: Optional[int] = 12) -> Iterable[Message]:
    """Get the sequence of messages that led to this message."""
    if limit < 1:
        raise ValueError("limit must be greater than 0")
    elif limit == 1 or message.reply_to is None:
        yield message
    else:
        yield from message_sequence(message.reply_to, limit=limit - 1)
        yield message


class UserConsoleNode(Node):
    role = "user"

    def receive(self, message: Message):
        pprint(message.dict())
        response = input("Enter response: ")
        yield Message(sender=self, content=response)


class ConsoleChat(StableChat):
    role = "system"

    def receive(self, message: Message):
        pprint(message.dict())
        for response in super().receive(message):
            pprint(response.dict())
