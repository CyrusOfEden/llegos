from abc import ABC, abstractmethod
from textwrap import dedent
from typing import List

from langchain.schema import BaseMemory
from pydantic import Field

from llambdao.message import Message, Node


class BOID(Node, ABC):
    class Directive(Message):
        role = "system"
        action = "be"
        content = dedent(
            """\
            You are an autonomous language model AI agent following the
            Beliefs, Obligations, Intentions, and Desires framework.

            You can be informed of your environment, of the world around you.
            You have a set of beliefs about your world, your metacognitive learnings.
            You have a set of desires about your world, virtues and values.
            Upon reflection, your desires and beliefs can be used to inspire goals.

            Some may want to talk with you, talk kindly, thoughtfully, and with care.

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
    do_model = Field(
        description="Agent's doer, like an autonomous agent like AutoGPT or BabyAGI"
    )
    chat_model = Field(description="Agent's chat model")

    def be(self, message: Message):
        """Operator can update agent's behavior."""
        self.behavior = message

    def do(self, message: Message):
        action = self.start_doing if not message.reply_to else self.continue_doing
        yield from action(message)

    @abstractmethod
    def start_doing(self, message: Message):
        raise NotImplementedError()

    @abstractmethod
    def continue_doing(self, message: Message):
        raise NotImplementedError()

    @abstractmethod
    def chat(self, message: Message):
        raise NotImplementedError()
