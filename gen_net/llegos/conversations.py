from abc import ABC, abstractmethod
from typing import Optional

from pydantic import InstanceOf

from gen_net.llegos.asyncio import propogate_all
from gen_net.llegos.networks import AsyncGenAgent, Field, GenNetwork, Message


class Converse(Message):
    method = "converse"


class ConversationalAgent(AsyncGenAgent, ABC):
    @abstractmethod
    async def converse(self, message: Converse) -> Optional[Converse]:
        """
        Decide to not resopnd or reply with a Converse, which is sent to its recipient
        """
        ...


class Conversation(GenNetwork):
    members: list[InstanceOf[ConversationalAgent]] = Field(min_items=2)

    async def converse(self, message: Converse):
        messages = [
            Converse.forward(message, sender=self, receiver=member)
            for member in self.members
            if member != message.sender
        ]
        async for reply in propogate_all(messages):
            yield reply
            yield reply
