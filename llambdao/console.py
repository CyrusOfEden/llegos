from pprint import pprint

from llambdao import Message, Node


class PrettyConsole(Node):
    role = "user"

    def tell(self, message: Message):
        pprint(message.dict())

    def request(self, message: Message):
        pprint(message.dict())
        response = input("Enter response: ")
        return Message(sender=self, content=response)
