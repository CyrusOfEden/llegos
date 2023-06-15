import os
from textwrap import dedent

import openai
from dotenv import load_dotenv
from pydantic import Field

from llambdao import Message
from llambdao.abc.asyncio import AsyncNode
from llambdao.helpers import ConsoleChat, UserConsoleNode

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")


class Philosopher(AsyncNode):
    role = "ai"  # can be one of "system", "user", "ai"
    short_term_memory: list[Message] = Field()

    class Directive(Message):
        role = "user"
        action = "be"

        def __init__(self, beliefs: str, **kwargs):
            return super().__init__(
                content=dedent(
                    f"""\
                    You are an AI that is playing the role of a philosopher.
                    You are one of a group of philosophers advising the user.

                    Here are your beliefs:
                    {beliefs}

                    """
                ),
                **kwargs,
            )

    def __init__(self, beliefs: str, **kwargs):
        short_term_memory = kwargs.pop("short_term_memory", [])
        if not any(short_term_memory):
            short_term_memory.append(self.Directive.draft(beliefs=beliefs))

        super().__init__(
            **kwargs,
            short_term_memory=short_term_memory,
        )

    def be(self, message: Message):
        self.short_term_memory[0] = message

    def inform(self, message: Message):
        self.short_term_memory.append(message)

    def chat(self, message: Message):
        """Ask a Philosopher a question"""
        completion = openai.Completion.create(
            engine="gpt-3.5-turbo",
            messages=[m.json() for m in self.short_term_memory],
            temperature=0.5,
            max_tokens=512,
            stop=["\n"],
        )

        response = Message(
            content=completion.choices[0].text, reply_to=message, action="ask"
        )
        # Update the local state
        self.short_term_memory.append(response)

        return response


def test_philosopher_dinner_party():
    user = UserConsoleNode()
    chat = ConsoleChat(
        user,
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
            sender=user,
            action="chat",
            content="What is the meaning of life?",
        )
    )
