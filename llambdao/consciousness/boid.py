from abc import ABC, abstractmethod
from textwrap import dedent
from typing import List

from langchain.schema import BaseMemory
from pydantic import Field

from llambdao.message import Message, Node, SystemMessage


class BOID(Node, ABC):
    # State
    memory: BaseMemory = Field(description="Agent's persistent memory")
    directive: Message = Field(
        default=SystemMessage(
            content=dedent(
                """\
                You are an autonomous language model AI agent following the
                Beliefs, Obligations, Intentions, and Desires framework.

                You can be informed of your environment, of the world around you.
                You have a set of beliefs about your world, your metacognitive learnings.
                You have a set of desires about your world, virtues and values.
                Upon reflection, your desires and beliefs can be used to inspire goals.

                Some may want to talk with you, talk kindly, thoughtfully, and with care.

                Others may tell you to do things, which you will do with care and attention.
                """
            ),
        ),
    )
    obligations: List[str] = Field(
        default_factory=list,
        description=dedent(
            """\
            An agent MUST perform its obligations.
            """
        ),
    )
    beliefs: List[str] = Field(
        default_factory=list,
        description=dedent(
            """\
            Beliefs represent the informational state of the agent about its world.
            Beliefs can include inference rules, allowing forward chaining to lead to new beliefs.
            Using the term belief rather than knowledge recognizes that they are dynamic, not fact.
            """
        ),
    )
    desires: List[str] = Field(
        default_factory=list,
        description=dedent(
            """\
            Desires represent the motivational state of the agent.
            They represent objectives or situations that the agent would like to accomplish.
            Examples of desires might be: find the best price, go to the party or become rich.
            """
        ),
    )
    intentions: List[str] = Field(
        default_factory=list,
        description=dedent(
            """\
            Intentions represent the current plan of the agent.
            Intentions are desires to which the agent has to some extent committed.
            """
        ),
    )

    def be(self, message: Message):
        self.directive = message

    @abstractmethod
    def do(self, message: Message):
        raise NotImplementedError()

    @abstractmethod
    def chat(self, message: Message):
        raise NotImplementedError()
