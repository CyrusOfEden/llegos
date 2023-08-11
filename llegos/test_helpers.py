from typing import Callable

from openai import ChatCompletion

from llegos.asyncio import AsyncBehavior
from llegos.ephemeral import EphemeralBehavior, EphemeralAgent, EphemeralMessage, Field
from llegos.messages import Ack


class SimpleGPTAgent(EphemeralAgent):
    language: Callable = Field(default=ChatCompletion.create, exclude=True)
    working_memory: list[EphemeralMessage] = Field(default_factory=list)
    short_term_memory: list[EphemeralMessage] = Field(default_factory=list)
    long_term_memory: list[EphemeralMessage] = Field(default_factory=list)


class AckAgent(EphemeralBehavior):
    receivable_messages: set[type[EphemeralMessage]] = Field(
        default={Ack}, exclude=True
    )

    def ack(self, message: Ack):
        return Ack.reply_to(message)


class AsyncAckAgent(AsyncBehavior, AckAgent):
    async def ack(self, message: Ack):
        return Ack.reply_to(message)
