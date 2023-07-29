from llegos.asyncio import AsyncAgent
from llegos.ephemeral import EphemeralAgent, EphemeralMessage
from llegos.messages import Ack, Inform


class MockAgent(EphemeralAgent):
    receivable_messages: set[type[EphemeralMessage]] = {Inform}

    def inform(self, message: Inform):
        yield Ack.reply_to(message, body=f"Ack: {message.id}")


class MockAsyncAgent(AsyncAgent, MockAgent):
    receivable_messages: set[type[EphemeralMessage]] = {Inform}

    async def inform(self, message: Inform):
        yield Ack.reply_to(message, body=f"Ack: {message.id}")
