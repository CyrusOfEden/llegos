from typing import Any

from langchain.schema import Document
from langchain.tools import BaseTool
from pydantic import Field

from llambdao import AbstractObject, Message, Node
from llambdao.asyncio import AsyncNode


class NodeTool(AbstractObject, BaseTool):
    """Turns a Node into a Tool that can be used by other agents."""

    node: Node = Field(init=False)

    def _run(self, body: str) -> str:
        response = self.node.receive(Message.request(body=body))
        return response.content

    async def _arun(self, body: str) -> str:
        raise NotImplementedError


class AsyncNodeTool(AbstractObject, BaseTool):
    """Turns an AsyncNode into an Async Tool that can be used by other agents."""

    node: AsyncNode = Field(init=False)

    def _run(self, body: str) -> str:
        raise NotImplementedError

    async def _run(self, body: str) -> str:
        response = await self.node.areceive(Message.draft_request(body=body))
        return response.content


class LangchainNode(Node):
    """
    By default, a LangchainNode will use the chain's run method to interpret messages.

    Nodes contain implementations for the messages they choose to receive.
    """

    chain: Any = Field(description="the chain to use to interpret messages")

    def tell(self, message: Message):
        document = Document(page_content=message.content, metadata=message.metadata)
        self.chain.memory.add_documents([document])

    def request(self, message: Message):
        yield self._draft(content=self.chain.run(message.content))


class PlanAndExecuteNode(LangchainNode):
    pass


class BabyAGINode(LangchainNode):
    def tell(self, message: Message):
        document = Document(page_content=message.content, metadata=message.metadata)
        # Have to override this method to add documents to chain.vectorstore instead of chain.memory
        self.chain.vectorstore.add_documents([document])

    def request(self, message: Message) -> Message:
        response = self.chain(inputs={"objective": message.content, **message.metadata})
        yield self._draft(content=response)


class AutoGPTNode(LangchainNode):
    def tell(self, message: Message):
        documents = [Document(page_content=message.content, metadata=message.metadata)]
        self.chain.memory.retriever.add_documents(documents)

    def request(self, message: Message) -> Message:
        """Can pass in multiple goals, separated by newlines."""
        goals = message.metadata.get("goals", message.content.split("\n"))
        response = self.chain.run(goals)
        yield self._draft(content=response)
