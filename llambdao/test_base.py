from typing import Iterable

from llambdao.base import ApplicatorNode, GroupChatNode, Message, Node


class Responder(Node):
    """
    This demonstrates a Node pattern for responding to particular events.

    In this case, upon receiving a message, the Responder will reply with message.content + "!"

    A Node `receive`s messages and can `yield` messages in response.
    You can think of `receive` as a function that takes a message and generates messages.

    Within `receive`, you can choose to interpet the message however you like.
    """

    role = "assistant"

    def receive(self, message: Message) -> Iterable[Message]:
        if not message.content.endswith("!!"):
            yield self.reply_to(message, content=f"{message.content}!")


def test_applicator_node():
    """
    ApplicatorNode is useful for having a group of nodes all work on the same message.

    In this case, we have three Responder nodes, and they will all respond to the same message.

    This operator is useful for having multiple agents do work on the same message.
    """

    a = Responder()
    b = Responder()
    c = Responder()
    applicator = ApplicatorNode([a, b, c])
    m = Message(content="test", role="user", sender_id=a.id, type="do")

    messages = list(applicator.receive(m))
    assert len(messages) == 3

    # (a, b, c) all respond to a message sent by a, or any other node
    assert messages[0].content == "test!"
    assert messages[0].sender_id == a.id
    assert messages[1].content == "test!"
    assert messages[1].sender_id == b.id
    assert messages[2].content == "test!"
    assert messages[2].sender_id == c.id


def test_group_chat_node():
    """
    A GroupChatNode broadcasts any received messages to all of its nodes,
    skipping the node that sent the message. Generated messages are continuously
    broadcasted until all nodes have processed all generated messages.
    """

    a = Responder()
    b = Responder()
    c = Responder()
    group = GroupChatNode([a, b, c])
    m = Message(content="test", role="user", sender_id=b.id, type="chat")

    messages = list(group.receive(m))
    assert len(messages) == 6

    # first, (a, c) respond to a message sent by b
    assert messages[0].content == "test!"
    assert messages[0].sender_id == a.id
    assert messages[1].content == "test!"
    assert messages[1].sender_id == c.id

    # then, (b, c) respond to messages[0] sent by a
    assert messages[2].content == "test!!"
    assert messages[2].sender_id == b.id
    assert messages[3].content == "test!!"
    assert messages[3].sender_id == c.id

    # finally, (a, b) respond to messages[1] sent by c
    assert messages[4].content == "test!!"
    assert messages[4].sender_id == a.id
    assert messages[5].content == "test!!"
    assert messages[5].sender_id == b.id
    assert messages[5].sender_id == b.id
