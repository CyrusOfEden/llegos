from langchain.chains.base import Chain
from langchain.schema import Document
from langchain.tools import BaseTool
from pydantic import Field

from llambdao import Message
from llambdao import Node as SyncNode
from llambdao.asyncio import AsyncNode


class NodeTool(BaseTool):
    """Turns a Node into a Tool that can be used by other agents."""
    node: SyncNode = Field()

    def _run(self, body: str) -> str:
        response = self.node.request(Message(body))
        return response.body


class AsyncNodeTool(BaseTool):
    """Turns an AsyncNode into an Async Tool that can be used by other agents."""
    node: AsyncNode = Field()

    async def _run(self, body: str) -> str:
        response = await self.node.arequest(Message(body))
        return response.body


class Node(SyncNode):
    chain: Chain

    """A Node that can plan and execute actions, and has no memory."""
    def request(self, message: Message) -> Message:
        return Message.reply_to(message, with_body=self.chain.run(message.body))


class BabyAGINode(Node):
    """
    Usage:

    >>> from langchain.experimental.autonomous_agents.baby_agi import BabyAGI
    >>> from lambdao.langchain import BabyAGINode
    >>> babyagi = BabyAGINode(BabyAGI.from_llm(...))
    >>> babyagi.inform(Message("The meaning of life is 42.", metadata={...}))
    >>> babyagi.request(Message("What is the meaning of life?", metadata={...}))
    """

    def inform(self, message: Message):
        document = Document(page_content=message.body, metadata=message.metadata)
        self.chain.vectorstore.add_documents([document])


class AutoGPTNode(Node):
    """
    Usage:

    >>> from langchain.experimental.autonomous_agents.autogpt import AutoGPT
    >>> from lambdao.langchain import AutoGPTNode
    >>> autogpt = AutoGPTNode(AutoGPT.from_llm_and_tools(...))
    >>> autogpt.inform(Message("The meaning of life is 42.", metadata={...}))
    >>> autogpt.request(Message("What is the meaning of life?", metadata={...}))
    """

    def inform(self, message: Message):
        document = Document(page_content=message.body, metadata=message.metadata)
        self.chain.memory.add_documents([document])

    def request(self, message: Message) -> Message:
        goals = message.body.split(", ")
        return Message.reply_to(message, with_body=self.chain.run(goals))

