from typing import Callable

from openai import ChatCompletion

from llegos.asyncio import AsyncRole
from llegos.ephemeral import EphemeralAgent, EphemeralMessage, EphemeralRole, Field
from llegos.messages import Ack


class SimpleGPTAgent(EphemeralAgent):
    language: Callable = Field(default=ChatCompletion.create, exclude=True)
    working_memory: list[EphemeralMessage] = Field(default_factory=list)
    short_term_memory: list[EphemeralMessage] = Field(default_factory=list)
    long_term_memory: list[EphemeralMessage] = Field(default_factory=list)


class AckAgent(EphemeralRole):
    receivable_messages: set[type[EphemeralMessage]] = Field(
        default={Ack}, exclude=True
    )

    def ack(self, message: Ack):
        return Ack.reply_to(message)


class AsyncAckAgent(AsyncRole, AckAgent):
    async def ack(self, message: Ack):
        return Ack.reply_to(message)
