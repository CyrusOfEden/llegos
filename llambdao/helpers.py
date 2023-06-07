from pprint import pprint
from typing import Iterable, List

from pydantic import Field

from llambdao.abc import Chat, Node
from llambdao.abc.asyncio import AsyncNode
from llambdao.message import Message


def message_sequence(message: Message) -> Iterable[Message]:
    """Get the sequence of messages that led to this message."""
    if message.reply_to is not None:
        yield from message_sequence(message.reply_to)
    yield message


def chat_messages(message: Message, directive: Message) -> List[Message]:
    """Help construct the messages list for a chat model"""
    return list(message_sequence(directive)) + list(message_sequence(message))


class ConsoleNode(Node):
    role = "user"

    def receive(self, message: Message):
        pprint(message.dict())
        response = input("Enter response: ")
        yield Message(sender=self, content=response)


class Group(Chat):
    log: List[Message] = Field(default_factory=list)

    def receive(self, message: Message):
        self.log.append(message)
        for response in super().receive(message):
            self.log.append(response)
            yield response


class AsyncGroup(Group, AsyncNode):
    def __init__(self, *nodes: AsyncNode, **kwargs):
        super().__init__(*nodes, **kwargs)

    async def areceive(self, message: Message):
        self.log.append(message)
        async for response in super().areceive(message):
            self.log.append(response)
            yield response
