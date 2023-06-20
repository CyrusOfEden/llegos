from pprint import pprint

from llambdao.message import Message
from llambdao.node import GroupChatNode, Node


class ConsoleHumanNode(Node):
    role = "user"

    def chat(self, message: Message):
        pprint(message.dict())
        response = input("Enter response: ")
        if response:
            yield Message(
                sender=self, content=response, intent="chat", reply_to=message
            )


class ConsoleGroupChatNode(GroupChatNode):
    role = "system"

    def chat(self, message: Message):
        pprint(message.dict())
        for response in super().chat(message):
            pprint(response.dict())
