from typing import Iterable

from llegos.messages import Ack
from llegos.test_utilities import MockAgent


class TestMockAgent:
    def test_agent_can_emit_event(self):
        agent = MockAgent()
        event_emitted = False

        def event_handler(message):
            nonlocal event_emitted
            event_emitted = True

        agent.add_listener("event", event_handler)
        agent.emit("event", "Hello, world!")

        assert event_emitted

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
        assert agent.receivable_messages == {Ack}

        message = Ack()
        response = agent.receive(message)
        assert isinstance(response, Iterable)

        reply: Ack = next(response)
        assert reply.intent == "ack"
        assert reply.parent == message
