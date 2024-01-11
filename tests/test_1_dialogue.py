"""
Autogen can be implemented in Llegos, but Llegos can't be implemented in Autogen.
"""


# matchref lets use use ref.a1, ref.a2, etc. to match on patterns in case statements
from matchref import ref

from llegos import research as llegos

"""
A message class that has some content.
"""


class ChatMessage(llegos.Message):
    content: str


class ChatBot(llegos.Actor):
    """
    Here we use response to mock the response in testing, but in a real
    application, you could use a model to generate a response.
    """

    response: str

    def receive_chat_message(self, message: ChatMessage):
        """
        `message`s of type `MessageClass` are dispatched
        to the `receive_{message_class}(message)` method.
        """
        return ChatMessage.reply_to(message, content=self.response)


class Dialogue(llegos.Network):
    def start(self):
        """
        Since actors can be a part of multiple networks, its important to
        scope their usage within the network by using `with {network}:`
        """
        return llegos.message_propogate(
            ChatMessage(
                content="Hello",
                sender=self.actors[0],
                receiver=self.actors[1],
            )
        )


def test_dialogue():
    a1 = ChatBot(response="Hello")
    a2 = ChatBot(response="Hi")
    # Every network has a list of actors
    dialogue = Dialogue(actors=[a1, a2])

    with dialogue:
        # get the first 5 messages
        for msg, _ in zip(dialogue.start(), range(4)):
            assert a1.network == dialogue, "the actor's network is dialogue"
            match msg:
                case ChatMessage(sender=ref.a1, receiver=ref.a2):
                    assert msg.content == a1.response
                case ChatMessage(sender=ref.a2, receiver=ref.a1):
                    assert msg.content == a2.response
