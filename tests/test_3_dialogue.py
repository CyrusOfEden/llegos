"""
Autogen can be implemented in Llegos, but Llegos can't be implemented in Autogen.
"""

from typing import Sequence

from matchref import ref
from pydantic import Field

from llegos import research as llegos


class ChatMessage(llegos.Message):
    content: str


class ChatBot(llegos.Actor):
    response: str

    def receive_chat_message(self, message: ChatMessage):
        return ChatMessage.reply_to(message, content=self.response)


class Dialogue(llegos.Scene):
    actors: Sequence[ChatBot] = Field(min_length=2, max_length=2)

    def converse(self):
        with self:
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
    scene = Dialogue(actors=[a1, a2])

    """
    3 back-and-forth messages are sufficient to test the scene.
    """
    for msg, _ in zip(scene.converse(), range(4)):
        match msg:
            case ChatMessage(sender=ref.a1, receiver=ref.a2):
                assert msg.content == a1.response
            case ChatMessage(sender=ref.a2, receiver=ref.a1):
                assert msg.content == a2.response
