from langchain.experimental.autonomous_agents.autogpt.agent import AutoGPT
from langchain.experimental.autonomous_agents.baby_agi import BabyAGI
from langchain.experimental.plan_and_execute import PlanAndExecute
from langchain.schema import Document
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


class PlanAndExecuteAgent(AbstractAgent, PlanAndExecute):
    def request(self, message: Message) -> Message:
        return Message.reply_to(message, with_body=self.run(message.body))


class BabyAGIAgent(AbstractAgent, BabyAGI):
    @classmethod
    def from_llm(cls, *args, **kwargs) -> "BabyAGIAgent":
        return super().from_llm(*args, **kwargs)

    def inform(self, message: Message):
        document = Document(page_content=message.body, metadata=message.metadata)
        self.vectorstore.add_documents([document])

    def request(self, message: Message) -> Message:
        return Message.reply_to(message, with_body=self.run(message.body))


class AutoGPTAgent(AbstractAgent, AutoGPT):
    @classmethod
    def from_llm_and_tools(cls, *args, **kwargs) -> "AutoGPTAgent":
        return super().from_llm_and_tools(*args, **kwargs)

    def inform(self, message: Message):
        document = Document(page_content=message.body, metadata=message.metadata)
        self.memory.add_documents([document])

    def request(self, message: Message) -> Message:
        goals = message.body.split(", ")
        return Message.reply_to(message, with_body=self.run(goals))

