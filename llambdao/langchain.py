from langchain import LLMChain
from langchain.tools import BaseTool
from pydantic import Field

from llambdao.message import Message
from llambdao.node import AbstractObject, Node
from llambdao.node.asyncio import AsyncNode


class NodeTool(AbstractObject, BaseTool):
    """Turns a Node into a Tool that can be used by other agents."""

    args_schema = Message
    node: Node = Field(init=False)

    def _run(self, **kwargs) -> str:
        return "\n\n".join(self.node.receive(Message(**kwargs)))

    async def _arun(self, *args, **kwargs) -> str:
        raise NotImplementedError()


class AsyncNodeTool(AbstractObject, BaseTool):
    """Turns an AsyncNode into an Async Tool that can be used by other agents."""

    args_schema: Message
    node: AsyncNode = Field(init=False)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError()

    async def _run(self, **kwargs) -> str:
        results = []
        async for response in self.node.areceive(Message(**kwargs)):
            results.append(response)
        return "\n\n".join(results)


class LangchainNode(Node):
    """
    By default, a LangchainNode will use the chain's run method to interpret messages.

    Nodes contain implementations for the messages they choose to receive.
    """

    chain: LLMChain = Field()

    def receive(self, message: Message):
        yield Message(sender=self, content=self.chain.run(message.content))
