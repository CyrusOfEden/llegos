from langchain.chains.base import Chain
from langchain.schema import Document
from langchain.tools import BaseTool
from pydantic import Field

from llambdao import Message, Node
from llambdao.asyncio import AsyncNode


class NodeTool(BaseTool):
    """Turns a Node into a Tool that can be used by other agents."""
    node: Node = Field()

    def _run(self, body: str) -> str:
        response = self.node.request(Message(body=body))
        return response.body


class AsyncNodeTool(BaseTool):
    """Turns an AsyncNode into an Async Tool that can be used by other agents."""
    node: AsyncNode = Field()

    async def _run(self, body: str) -> str:
        response = await self.node.arequest(Message(body=body))
        return response.body


class LangchainNode(Node):
    chain: Chain

    def request(self, message: Message) -> Message:
        return Message.reply_to(message, with_body=self.chain.run(message.body))


class BabyAGINode(LangchainNode):
    def inform(self, message: Message):
        document = Document(page_content=message.body, metadata=message.metadata)
        self.chain.vectorstore.add_documents([document])


class AutoGPTNode(LangchainNode):
    def inform(self, message: Message):
        document = Document(page_content=message.body, metadata=message.metadata)
        self.chain.memory.add_documents([document])

    def request(self, message: Message) -> Message:
        goals = message.body.split(", ")
        return Message.reply_to(message, with_body=self.chain.run(goals))

