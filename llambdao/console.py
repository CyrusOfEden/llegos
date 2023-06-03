from pprint import pprint

from llambdao import Message, Node


class PrettyConsole(Node):
    role = "user"

    def inform(self, message: Message):
        pprint(message.dict())

    def request(self, message: Message):
        pprint(message.dict())
        response = input("Enter response: ")
        return Message.draft_reply(message, with_content=response)
