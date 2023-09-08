from os import environ as env
from random import sample
from textwrap import dedent

from cursive import Cursive
from dotenv import load_dotenv

from llegos.cursive import to_openai_json
from llegos.research import Actor, Message, Scene, message_chain, send

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
    model: Cursive
    system_prompt: str  # immutable values go on the actor

    def on_message(self, message: Message) -> Message | None:
        model_messages = to_openai_json(message_chain(message, height=8))
        return self.model.ask(
            system_message=dedent(
                f"""\
                {jeremy_howard_system}

                {self.system_prompt}

                Your ID is {self.id}

                Be concise, and to the point. Answer in 4 sentences or less.
                """
            ),
            messages=model_messages,
            prompt=dedent(
                """\
                First, think carefully whether you have value to add to the conversation.
                You can add value by refining a comment, criticising a comment, adding perspective,
                or asking a question.
                """
            ),
            function_call=Message,
        ).function_result


class BoardOfDirectors(Scene):
    members: set[BoardMember]

    def on_message(self, message: Message):
        receiver = sample(self.members, 1)[0]
        return Message.forward(message, to=receiver)


if __name__ == "__main__":
    load_dotenv()

    cursive = Cursive(openrouter={"api_key": env["OPENAI_API_KEY"]})

    board = BoardOfDirectors(
        members={
            BoardMember(
                model=cursive,
                system_prompt="You are Sam Altman; pragmatic, lean, and action-oriented.",
            ),
            BoardMember(
                model=cursive,
                system_prompt="You're are Paul Graham, quite insightful, and poetic.",
            ),
            BoardMember(
                model=cursive,
                system_prompt="You are Simon Cowell, condescending and snarky and witty.",
            ),
            BoardMember(
                model=cursive,
                system_prompt="You are Gordon Ramsey, and you can get angry really quickly.",
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

    with board.scene():
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
