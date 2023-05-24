from langchain.tools import BaseTool
from pydantic import Field

from llambdao import AbstractAgent, Message
from llambdao.asyncio import AbstractAsyncAgent


class AgentTool(BaseTool):
    agent: AbstractAgent = Field()

    def _run(self, body: str) -> str:
        response = self.agent.request(Message(body))
        return response.body


class AsyncAgentTool(BaseTool):
    agent: AbstractAsyncAgent = Field()

    async def _run(self, body: str) -> str:
        response = await self.agent.arequest(Message(body))
        return response.body
