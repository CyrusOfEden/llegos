from textwrap import dedent
from typing import List

from langchain.chat_models import ChatOpenAI
from langchain.schema import BaseMemory
from pydantic import Field

from llambdao import Message, Node
from llambdao.helpers import chat_messages


class BOIDAgent(Node):
    class Directive(Message):
        role = "user"  # works better than "system"... for now... with GPTs
        action = "be"
        content = dedent(
            """\
            You are an autonomous attention machine following the BDI framework.
            You can be informed of your environment, of the world around you.
            You have a set of beliefs about your world, your metacognitive learnings.
            You have a set of desires about your world, virtues and values.
            Upon reflection, your desires and beliefs can be used to inspire goals.
            Others may request you to think and do, to manifest intention into action.
            You are an expert at this.
            Some may ask you simple questions, which you will answer thoughtfully and concisely,
            indicating your level of confidence in your claims.
            Others may tell you to do things, which you will do with the utmost care and attention.
            """
        )

    # State
    memory: BaseMemory = Field(description="Agent's persistent memory")
    behavior: Message = Directive()  # to be injected as the system prompt
    obligations: List[str] = Field(default_factory=list)
    beliefs: List[str] = Field(default_factory=list)
    desires: List[str] = Field(default_factory=list)
    intentions: List[str] = Field(default_factory=list)

    # Models
    be_model = Field(description="Agent's model for revising behaviour")
    do_model = Field(description="Agent's do model")
    chat_model: ChatOpenAI = Field(
        description="Agent's chat model", default_factory=ChatOpenAI
    )

    def be(self, message: Message):
        """Operator can update agent's behavior."""
        self.behavior = message

    def do(self, message: Message):
        if message.reply_to:
            """A continuation of a previous action."""
            # load necessary state from persistent memory
            # perform autonomous agent operations, i.e. AutoGPT here
        else:
            """A new action."""

    def chat(self, message: Message):
        """Ask a question."""
        result = self.chat_model.generate(
            [chat_messages(message, directive=self.behavior)], stop=["\n"]
        )
        return Message(content=result, reply_to=message)
