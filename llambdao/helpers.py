from typing import Iterable, List

from llambdao import Message


def message_sequence(message: Message) -> Iterable[Message]:
    """Get the sequence of messages that led to this message."""
    if message.reply_to is not None:
        yield from message_sequence(message.reply_to)
    yield message


def chat_messages(message: Message, directive: Message) -> List[Message]:
    """Help construct the messages list for a chat model"""
    return list(message_sequence(directive)) + list(message_sequence(message))
