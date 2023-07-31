from llegos.asyncio import AsyncAgent
from llegos.ephemeral import EphemeralAgent, EphemeralMessage
from llegos.messages import Ack


class ChatMessage(EphemeralMessage):
    body: str


class MockAgent(EphemeralAgent):
    receivable_messages: set[type[EphemeralMessage]] = {Ack}

    def ack(self, message: Ack):
        yield Ack.reply_to(message)


class MockAsyncAgent(AsyncAgent, MockAgent):
    receivable_messages: set[type[EphemeralMessage]] = {Ack}

    async def ack(self, message: Ack):
        yield Ack.reply_to(message)
