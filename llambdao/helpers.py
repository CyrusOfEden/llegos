from pprint import pprint

from llambdao.base import GroupChatNode, UserNode
from llambdao.message import Message


class ConsoleHumanNode(UserNode):
    def chat(self, message: Message):
        pprint(message.dict())
        response = input("Enter response: ")
        if response:
            yield Message(
                sender_id=self, content=response, type="chat", parent_id=message
            )


class ConsoleGroupChatNode(GroupChatNode):
    def chat(self, message: Message):
        pprint(message.dict())
        for response in super().chat(message):
            pprint(response.dict())
