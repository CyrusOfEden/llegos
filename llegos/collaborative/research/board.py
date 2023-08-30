from os import environ as env
from random import sample
from textwrap import dedent
from typing import Callable

from dotenv import load_dotenv

from llegos.functional import use_model
from llegos.research import Actor, Context, Message, send


def model(*args, **kwargs):
    return openai.ChatCompletion.create(
        model="anthropic/claude-instant-v1",
        headers={
            "HTTP-Referer": "https://llegos.substack.com",
            "X-Title": "Playing with Llegos",
        },
        *args,
        **kwargs,
    )


jeremy_howard_system = """\
You are an autoregressive language model that has been fine-tuned with
instruction-tuning and RLHF. You carefully provide accurate, factual,
thoughtful, nuanced answers, and are brilliant at reasoning.
If you think there might not be a correct answer, you say so.

Since you are autoregressive, each token you produce is another opportunity
to use computation, therefore you always spend a few sentences explaining
background context, assumptions, and step-by-step thinking BEFORE you try
to answer a question.
"""


class BoardMember(Actor):
    model: Callable = model
    system_prompt: str  # immutable values go on the actor

    def on_message(self, message: Message) -> Message | None:
        model_kwargs = use_model(
            max_tokens=384,
            system=f"""\
            {jeremy_howard_system}

            {self.system_prompt}

            Your ID is {self.id}.

            Be concise, and to the point. Answer in 4 sentences or less.
            """,
            context=message,
            context_history=8,
            prompt="""\
            First, think carefully whether you have value to add to the conversation.
            You can add value by refining a comment, criticising a comment, adding perspective,
            or asking a question. If you find the conversation is repeating itself, return "STOP".

            Your additional directives are:
            """,
        )

        completion = self.model(**model_kwargs)

        response = completion.choices[0].message.content
        if "STOP" not in response:
            "Sends the Message to the BoardOfDirectors"
            return Message.reply_to(message, content=response)


class BoardOfDirectors(Context):
    members: set[BoardMember]

    def on_message(self, message: Message):
        receiver = sample(self.members, 1)[0]
        yield Message.forward(message, to=receiver)


if __name__ == "__main__":
    import openai

    load_dotenv()

    openai.api_base = "https://openrouter.ai/api/v1"
    openai.api_key = env["OPENAI_API_KEY"]

    board = BoardOfDirectors(
        members={
            BoardMember(
                system_prompt="You are Sam Altman; pragmatic, lean, and action-oriented.",
            ),
            BoardMember(
                name="Paul Graham",
                system_prompt="You're are Paul Graham, quite insightful, and poetic.",
            ),
            BoardMember(
                system_prompt="You are Simon Cowell, condescending and snarky and witty.",
            ),
            BoardMember(
                system_prompt="You are Gordon Ramsey, and you can get angry really quickly."
            ),
        },
    )

    prompt = Message.to(
        board,
        content="How should I think about my GTM strategy for a ghost kitchens product?",
    )

    def send_and_propogate(message: Message):
        for reply in send(message):
            yield reply
            yield from send_and_propogate(reply)

    with board.context():
        for reply in send_and_propogate(prompt):
            print(
                dedent(
                    f"""\
                    From: {reply.sender}
                    To: {reply.receiver}
                    Message: {reply.content}

                    """
                )
            )
