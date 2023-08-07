from typing import Callable

from openai import ChatCompletion

from llegos.asyncio import AsyncActor
from llegos.ephemeral import (EphemeralActor, EphemeralAgent, EphemeralMessage,
                              Field)
from llegos.messages import Ack


class SimpleGPTCognition(EphemeralAgent):
    language: Callable = Field(default=ChatCompletion.create, exclude=True)
    working_memory: list[EphemeralMessage] = Field(default_factory=list)
    short_term_memory: list[EphemeralMessage] = Field(default_factory=list)
    long_term_memory: list[EphemeralMessage] = Field(default_factory=list)


class AckAgent(EphemeralActor):
    receivable_messages: set[type[EphemeralMessage]] = Field(
        default={Ack}, exclude=True
    )

    def ack(self, message: Ack):
        return Ack.reply_to(message)


class AsyncAckAgent(AsyncActor, AckAgent):
    async def ack(self, message: Ack):
        return Ack.reply_to(message)
