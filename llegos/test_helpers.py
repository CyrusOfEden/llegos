from typing import Callable

from openai import ChatCompletion

from llegos.asyncio import AsyncActor
from llegos.ephemeral import EphemeralActor, EphemeralAgent, EphemeralMessage, Field
from llegos.messages import Ack


class ChatMessage(EphemeralMessage):
    body: str


class MockCognition(EphemeralAgent):
    language: Callable = Field(default=ChatCompletion.create, exclude=True)
    working_memory: list[EphemeralMessage] = Field(default_factory=list)
    short_term_memory: list[EphemeralMessage] = Field(default_factory=list)
    long_term_memory: list[EphemeralMessage] = Field(default_factory=list)


class MockAgent(EphemeralActor):
    cognition: MockCognition = Field(default_factory=MockCognition)
    receivable_messages: set[type[EphemeralMessage]] = Field(
        default={Ack}, exclude=True
    )

    def ack(self, message: Ack):
        return Ack.reply_to(message)


class MockAsyncAgent(AsyncActor):
    cognition: MockCognition = Field(default_factory=MockCognition)
    receivable_messages: set[type[EphemeralMessage]] = Field(
        default={Ack}, exclude=True
    )

    async def ack(self, message: Ack):
        return Ack.reply_to(message)
