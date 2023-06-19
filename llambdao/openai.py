from typing import List, Union

from llambdao.message import Message


def to_openai(message: Union[Message, List[Message]]):
    """Convert a Message or list of Messages to the OpenAI message format"""
    if isinstance(message, Message):
        return message.openai()
    elif isinstance(message, list):
        return [message.openai() for message in message]
    else:
        raise TypeError(f"Cannot convert {type(message)} to OpenAI message")
