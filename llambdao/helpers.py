from pprint import pprint

from llambdao.message import Message
from llambdao.node import GroupChatNode, Node


class ConsoleHumanNode(Node):
    role = "user"

    def chat(self, message: Message):
        pprint(message.dict())
        response = input("Enter response: ")
        yield Message(sender=self, content=response)


class ConsoleGroupChatNode(GroupChatNode):
    role = "system"

    def __init__(self, *args, **kwargs):
        super().__init__(ConsoleHumanNode(), *args, **kwargs)

    def chat(self, message: Message):
        pprint(message.dict())
        for response in super().chat(message):
            pprint(response.dict())
