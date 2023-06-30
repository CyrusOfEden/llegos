from pprint import pprint

from llambdao.base import GroupChatNode, Message, UserNode


class ConsoleHumanNode(UserNode):
    """
    A helper class for testing systems that gives an operator a console for responding to messages.
    """

    def chat(self, message: Message):
        pprint(message.dict())
        response = input("Enter response: ")
        if response:
            yield self.reply_to(message, response)


class ConsoleGroupChatNode(GroupChatNode):
    """
    A helper class for testing GroupChatNode that logs all messages to the console.
    """

    def chat(self, message: Message):
        for response in super().chat(message):
            pprint(response.dict())
            yield response
