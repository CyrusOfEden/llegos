from langchain import LLMChain
from pydantic import Field

from llambdao.message import Message
from llambdao.node.asyncio import AsyncNode
from llambdao.node.sync import Node


class LangchainNode(Node):
    """
    By default, a LangchainNode will use the chain's run method to interpret messages.

    Nodes contain implementations for the messages they choose to receive.
    """

    role = "assistant"
    chain: LLMChain = Field()

    def receive(self, message: Message):
        yield Message(sender=self, content=self.chain.run(message.content))


class AsyncLangchainNode(LangchainNode, AsyncNode):
    async def areceive(self, message: Message):
        yield Message(sender=self, content=self.chain.arun(message.content))
