from pprint import pprint
from typing import Iterable, Optional

from llambdao.abc import Chat, Node
from llambdao.message import Message


def message_sequence(message: Message, limit: Optional[int] = 12) -> Iterable[Message]:
    """Get the sequence of messages that led to this message."""
    if limit > 1 and message.reply_to is not None:
        yield from message_sequence(message.reply_to, limit=limit - 1)
    yield message


class UserConsoleNode(Node):
    role = "user"

    def receive(self, message: Message):
        pprint(message.dict())
        response = input("Enter response: ")
        yield Message(sender=self, content=response)


class ConsoleChat(Chat):
    role = "system"

    def receive(self, message: Message):
        pprint(message.dict())
        for response in super().receive(message):
            pprint(response.dict())
