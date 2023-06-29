from pprint import pprint

from llambdao.message import Message
from llambdao.sync import GroupChatNode, Node


class ConsoleHumanNode(Node):
    role = "user"

    def chat(self, message: Message):
        pprint(message.dict())
        response = input("Enter response: ")
        if response:
            yield Message(
                sender_id=self, content=response, type="chat", parent_id=message
            )


class ConsoleGroupChatNode(GroupChatNode):
    role = "system"

    def chat(self, message: Message):
        pprint(message.dict())
        for response in super().chat(message):
            pprint(response.dict())
