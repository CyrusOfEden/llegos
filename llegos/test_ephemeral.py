from typing import Iterable

import pytest

from llegos.ephemeral import EphemeralAgent, EphemeralMessage


class Inform(EphemeralMessage):
    intent = "inform"


class Ack(EphemeralMessage):
    intent = "ack"


class MockAgent(EphemeralAgent):
    def inform(self, message: Inform):
        yield Ack.reply(message, body=f"Ack: {message.id}")


class TestEphemeralMessage:
    def test_create_message_with_standard_fields(self):
        message = EphemeralMessage(
            intent="chat",
            body="Hello, world!",
            sender=MockAgent(),
            receiver=MockAgent(),
        )
        assert message.intent == "chat"
        assert message.body == "Hello, world!"
        assert isinstance(message.sender, EphemeralAgent)
        assert isinstance(message.receiver, EphemeralAgent)
        assert message.reply_to is None

    # Tests that a reply message is created correctly
    def test_create_reply_message(self):
        message = EphemeralMessage(
            intent="chat",
            body="Hello, world!",
            sender=MockAgent(),
            receiver=MockAgent(),
        )
        reply = EphemeralMessage.reply(message, body="Reply", intent="reply")
        assert reply.intent == "reply"
        assert reply.body == "Reply"
        assert reply.sender == message.receiver
        assert reply.receiver == message.sender
        assert reply.reply_to == message

    # Tests that a forward message is created correctly
    def test_create_forward_message(self):
        message = EphemeralMessage(
            intent="chat",
            body="Hello, world!",
            sender=MockAgent(),
            receiver=MockAgent(),
        )
        forward_message = EphemeralMessage.forward(message, intent="chat")
        assert forward_message.intent == "chat"
        assert forward_message.body == "Hello, world!"
        assert forward_message.sender == message.receiver
        assert forward_message.receiver is None
        assert forward_message.reply_to == message

    # Tests that a ValueError is raised when creating a message with an invalid sender
    def test_invalid_sender(self):
        with pytest.raises(ValueError):
            EphemeralMessage(
                intent="chat",
                body="Hello, world!",
                sender="invalid sender",
                receiver=MockAgent(),
            )

    # Tests that an exception is raised when creating a message with an invalid receiver
    def test_invalid_receiver(self):
        with pytest.raises(ValueError):
            EphemeralMessage(
                intent="chat",
                body="Hello, world!",
                sender=MockAgent(),
                receiver="invalid_receiver",
            )

    # Tests that creating a message with an invalid reply_to raises an exception
    def test_invalid_reply_to(self):
        with pytest.raises(ValueError):
            EphemeralMessage(
                intent="chat",
                body="Hello, world!",
                sender=MockAgent(),
                receiver=MockAgent(),
                reply_to="invalid",
            )

    # Tests that creating a message with an invalid created_at raises a ValueError
    def test_invalid_created_at(self):
        with pytest.raises(ValueError):
            EphemeralMessage(
                intent="chat",
                body="Hello, world!",
                sender=MockAgent(),
                receiver=MockAgent(),
                created_at="invalid",
            )

    # Tests that the role of a message is derived from the role of the sender
    def test_message_role_derived_from_sender_role(self):
        sender = EphemeralAgent(role="system")
        receiver = EphemeralAgent(role="user")
        message = EphemeralMessage(
            intent="chat",
            body="Hello, world!",
            sender=sender,
            receiver=receiver,
        )
        assert message.role == "system"


class TestEphemeralAgent:
    # Tests that the agent can emit an event
    def test_agent_can_emit_event(self):
        agent = MockAgent()
        event_emitted = False

        def event_handler(message):
            nonlocal event_emitted
            event_emitted = True

        agent.add_listener("event", event_handler)
        agent.emit("event", "Hello, world!")

        assert event_emitted

    # Tests that the agent can remove a listener from an event
    def test_remove_listener(self):
        agent = MockAgent()
        event_name = "test_event"

        def listener():
            return

        agent.add_listener(event_name, listener)
        assert listener in agent.listeners(event_name)
        agent.remove_listener(event_name, listener)
        assert listener not in agent.listeners(event_name)

    def test_agent_receive_message(self):
        agent = MockAgent()
        message = Inform(body="Hello, world!")
        response = agent.receive(message)
        assert isinstance(response, Iterable)
        assert next(response).body == f"Ack: {message.id}"

    # Tests that the agent can correctly retrieve a set of receivable intents
    def test_get_receivable_intents(self):
        agent = MockAgent()
        agent.receivable_messages = {Inform}
        assert agent.receivable_intents == {"inform"}
