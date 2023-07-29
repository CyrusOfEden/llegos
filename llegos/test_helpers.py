from llegos.asyncio import AsyncAgent
from llegos.ephemeral import EphemeralAgent, EphemeralMessage
from llegos.messages import Intent


class Inform(EphemeralMessage):
    intent: Intent = "inform"


class Ack(EphemeralMessage):
    intent: Intent = "ack"


class MockAgent(EphemeralAgent):
    receivable_messages: set[type[EphemeralMessage]] = {Inform}

    def inform(self, message: Inform):
        yield Ack.reply_to(message, body=f"Ack: {message.id}")


class MockAsyncAgent(AsyncAgent, MockAgent):
    async def inform(self, message: Inform):
        yield Ack.reply_to(message, body=f"Ack: {message.id}")
