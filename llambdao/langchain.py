from langchain import LLMChain
from pydantic import Field

from llambdao.asyncio import AsyncNode
from llambdao.base import AssistantNode, Message


class LangchainNode(AssistantNode):
    """
    By default, a LangchainNode will use the chain's run method to interpret messages.

    Nodes contain implementations for the messages they choose to receive.
    """

    role = "assistant"
    chain: LLMChain = Field()

    def receive(self, message: Message):
        content = self.chain.run(message.content)
        yield self.reply_to(message, content)


class AsyncLangchainNode(LangchainNode, AsyncNode):
    async def areceive(self, message: Message):
        content = await self.chain.arun(message.content)
        yield self.reply_to(message, content)
