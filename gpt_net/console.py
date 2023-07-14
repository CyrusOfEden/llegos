from pprint import pprint

from gpt_net.node import Message, UserNode


class ConsoleHumanNode(UserNode):
    """
    A helper class for testing systems that gives an operator a console for responding to messages.
    """

    def receive(self, message: Message):
        if message.type in {"chat", "request", "query"}:
            pprint(message.dict())
            response = input("Enter response: ")
            if response:
                yield self.reply_to(message, response)
        else:
            yield from super().receive(message)
