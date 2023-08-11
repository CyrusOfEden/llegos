import pytest

from llegos.messages import Chat, message_list
from llegos.test_helpers import Ack, AckAgent


class MessagesTest:
    def test_message_init(self):
        message = Ack(
            sender=AckAgent(),
            receiver=AckAgent(),
        )
        assert message.intent == "ack"
        assert isinstance(message.sender, AckAgent)
        assert isinstance(message.receiver, AckAgent)
        assert message.parent is None

    def test_message_reply_to(self):
        message = Ack(
            sender=AckAgent(),
            receiver=AckAgent(),
        )
        reply = Ack.reply_to(message)
        assert reply.intent == "ack"
        assert reply.sender == message.receiver
        assert reply.receiver == message.sender
        assert reply.parent == message

    def test_message_forward(self):
        message = Ack(
            sender=AckAgent(),
            receiver=AckAgent(),
        )
        new_receiver = AckAgent()
        fwd = Ack.forward(message, to=new_receiver)

        assert fwd.intent == "ack"
        assert fwd.sender == message.receiver
        assert fwd.receiver is None
        assert fwd.parent == message

    def test_message_role_derived_from_sender_role(self):
        sender = AckAgent(role="system")
        message = Ack(
            body="Hello, world!",
            sender=sender,
        )
        assert message.role == "system"

    def test_invalid_sender(self):
        with pytest.raises(ValueError):
            Ack(
                sender="invalid sender",
                receiver=AckAgent(),
            )

    def test_invalid_receiver(self):
        with pytest.raises(ValueError):
            Ack(
                sender=AckAgent(),
                receiver="invalid_receiver",
            )

    def test_invalid_parent(self):
        with pytest.raises(ValueError):
            Ack(
                sender=AckAgent(),
                receiver=AckAgent(),
                parent="invalid",
            )

    def test_invalid_created_at(self):
        with pytest.raises(ValueError):
            Ack(
                sender=AckAgent(),
                receiver=AckAgent(),
                created_at="invalid",
            )


class TestMessageList:
    def test_replies(self):
        m1 = Chat(message="Initial message", intent="chat")
        m2 = Chat(message="First reply", parent=m1, intent="chat")
        m2_1 = Chat(message="Second reply", parent=m2, intent="chat")
        m2_2 = Chat(message="Third reply", parent=m2, intent="chat")

        assert message_list(m2_1) == [m1, m2, m2_1]
        assert message_list(m2_2, height=2) == [m2, m2_2]
