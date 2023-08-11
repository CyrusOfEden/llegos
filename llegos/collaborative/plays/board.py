from textwrap import dedent

from dotenv import load_dotenv

from llegos.contexts import Context, ContextualRole, Field, Propagate
from llegos.functional import use_gen_model
from llegos.messages import Chat
from llegos.test_helpers import SimpleGPTAgent


class BoardMember(ContextualRole):
    name: str = Field(include=True)

    def chat(self, received_chat_message: Chat) -> Chat | None:
        model_kwargs = use_gen_model(
            model="gpt-3.5-turbo-0613",
            max_tokens=384,
            system=f"""\
            You are an autoregressive language model that has been fine-tuned with
            instruction-tuning and RLHF. You carefully provide accurate, factual,
            thoughtful, nuanced answers, and are brilliant at reasoning.
            If you think there might not be a correct answer, you say so.

            Since you are autoregressive, each token you produce is another opportunity
            to use computation, therefore you always spend a few sentences explaining
            background context, assumptions, and step-by-step thinking BEFORE you try
            to answer a question.

            You are {self.name} with ID {self.id} in a board meeting.
            The following are the latest messages in the board meeting.

            Be concise, and to the point. Answer in 4 sentences or less.
            """,
            context=received_chat_message,
            context_history=8,
            prompt=f"""\
            First, think carefully whether you have value to add to the conversation.
            You can add value by refining a comment, criticising a comment, adding perspective,
            or asking a question. If you find the conversation is repeating itself, return "STOP".

            Respond as {self.name}

            Your additional directives are:
            {self.system}
            """,
        )

        completion = self.agent.language(**model_kwargs)

        response = completion.choices[0].message.content
        if "STOP" not in response:
            return Chat.reply_to(received_chat_message, message=response)


class Board(Context):
    members: set[BoardMember] = Field()

    def chat(self, chat: Chat):
        for member in self.members:
            if member != chat.sender:
                yield Chat.forward(chat, to=member)


if __name__ == "__main__":
    load_dotenv()

    agent = SimpleGPTAgent()

    board = Board(
        system="board chat",
        agent=agent,
        members={
            BoardMember(
                name="Sam Altman",
                system="You are pragmatic, lean, and action-oriented.",
                agent=agent,
            ),
            BoardMember(
                name="Paul Graham",
                system="You're quite insightful, and poetic.",
                agent=agent,
            ),
            BoardMember(
                name="Simon Cowell",
                system="You are condescending and snarky and witty.",
                agent=agent,
            ),
            BoardMember(
                name="Gordon Ramsey",
                system="You actually care a lot, but you can get angry really quickly.",
                agent=agent,
            ),
        },
    )

    prompt = Chat(
        message="How should I think about my GTM strategy for a ghost kitchens product?",
        receiver=board,
    )

    for response in board.send(Propagate(message=prompt)):
        if response.receiver != board:
            print(
                dedent(
                    f"""\
                    From: {response.sender}
                    To: {response.receiver}
                    Message: {response.message}

                    """
                )
            )
