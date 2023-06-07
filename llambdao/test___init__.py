import os
from textwrap import dedent

import openai
from dotenv import load_dotenv
from pydantic import Field

from llambdao.console import PrettyConsole
from llambdao.message import Message, Node
from llambdao.recipes import Chat

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")


class Philosopher(Node):
    role = "ai"  # can be one of "system", "user", "ai"
    beliefs: str = Field(description="The beliefs of the philospher")
    memory: list[Message] = Field(init=False)

    class Directive(Message):
        """Subclass standard objects within your classes to remove duplication of prompts"""

        role = "user"
        action = "be"

        def __init__(self, content: str, **kwargs):
            return super().__init__(
                content=dedent(
                    f"""\
                    You are an AI that is playing the role of a philosopher.
                    You are one of a group of philosophers advising the user.

                    Here is how you think:
                    {content}

                    """
                ),
                **kwargs,
            )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.memory = [self.Directive.draft(self.beliefs)]

    def tell(self, message):
        """
        Nodes can have multiple methods. This one is called tell.

        Here we have it update the beliefs of the philosopher.
        """
        completion = openai.Completion.create(
            engine="gpt-3.5-turbo",
            messages=[self.memory[0], self.Reflection.draft(message.content)],
            temperature=0.25,
            max_tokens=512,
            stop=["DONE"],
        )
        self.memory[0] = self.Directive(content=completion.choices[0].text)

    def ask(self, message):
        """Ask a Philosopher a question"""
        completion = openai.Completion.create(
            engine="gpt-3.5-turbo",
            messages=[m.json() for m in self.memory],
            temperature=0.5,
            max_tokens=512,
            stop=["\n"],
        )

        response = Message(
            content=completion.choices[0].text, reply_to=message, action="ask"
        )
        # Update the local state
        self.memory.append(response)

        return response


def test_philosopher_dinner_party():
    human_in_the_loop = PrettyConsole()
    chat = Chat(
        human_in_the_loop,
        Philosopher(
            beliefs="I am the Sufi mystic poet Rumi, and I write beautiful prose."
        ),
        Philosopher(
            beliefs="I am the Taoist philosopher Lao Tzu, and I speak of the Tao."
        ),
        Philosopher(
            beliefs="I am the Zen philosopher Alan Watts, and I speak mystically."
        ),
        Philosopher(
            beliefs="I am the Buddhist philosopher Rob Burbea, and I speak of sacredness."
        ),
    )
    chat.receive(
        Message(
            action="ask",
            content="What is the meaning of life?",
            sender=human_in_the_loop,
        )
    )
