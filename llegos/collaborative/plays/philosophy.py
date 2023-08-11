import json
from pprint import pprint

from dotenv import load_dotenv

from llegos.collaborative.abstract.pairwise import PairwiseContext
from llegos.contexts import ContextualRole, Propagate
from llegos.ephemeral import EphemeralMessage, Field
from llegos.functional import use_actor_message, use_gen_model, use_reply_to
from llegos.messages import Ack, Chat
from llegos.test_helpers import SimpleGPTAgent


class Quality(Ack):
    "Quality is good, no further refinement is needed."


class Consider(EphemeralMessage):
    "Consider the material."


class Refine(EphemeralMessage):
    "Think, reason, and refine a response."
    thought: str = Field(include=True, description="think about how we can refine this")
    reasoning: str = Field(include=True, description="explain your reasoning")
    response: str = Field(include=True)


class Philosopher(ContextualRole):
    receivable_messages: set[type[EphemeralMessage]] = Field(
        default={Consider, Refine}, exclude=True
    )

    def consider(self, c: Consider) -> Refine:
        model_kwargs = use_gen_model(
            model="gpt-3.5-turbo-0613",
            max_tokens=768,
            system=f"You are {self.system}.",
            context=c,
            context_history=8,
            prompt="""\
            First, review and analyze the information.
            Then, decide who to talk to about it to.
            Use Refine to think, reason, and form an initial response.
            """,
        )
        function_kwargs, function_call = use_actor_message(
            self.receivers(Refine), {Refine}, sender=self, parent=c
        )

        completion = self.cognition.language(**model_kwargs, **function_kwargs)

        message: Refine = function_call(completion)  # to another agent
        return message

    def refine(self, r: Refine):
        model_kwargs = use_gen_model(
            model="gpt-3.5-turbo-0613",
            max_tokens=768,
            system=f"You are {self.system}.",
            context=r,
            context_history=8,
            prompt="""\
            First, review the material.
            If you are satisfied with its quality, elegance and insight,
            then return Quality.
            Else, use Refine to think, reason, and refine the response.
            """,
        )
        function_kwargs, function_call = use_reply_to(r, {Quality, Refine})

        completion = self.cognition.language(**model_kwargs, **function_kwargs)

        message: Quality | Refine = function_call(completion)
        return message

    def chat(self, c: Chat):
        "Sometimes GPT returns an assistant Chat message, handle it here."


class Prompt(EphemeralMessage):
    content: str = Field(include=True)


class DidacticContext(PairwiseContext):
    def prompt(self, message: Prompt):
        for agent in self.agents:
            yield Consider.forward(message, to=agent)


if __name__ == "__main__":
    load_dotenv()

    cognition = SimpleGPTAgent()

    ensemble = DidacticContext(
        agent=cognition,
        system="ensemble",
        agents={
            Philosopher(cognition=cognition, system="Kieerkegard"),
            Philosopher(cognition=cognition, system="Rumi"),
            Philosopher(cognition=cognition, system="Laotzu"),
            Philosopher(cognition=cognition, system="Buddha"),
            Philosopher(cognition=cognition, system="Alan Watts"),
        },
    )

    question = Prompt(
        content="How can one channel love into the world?",
        receiver=ensemble,
    )

    for m in ensemble.send(Propagate(message=question)):
        pprint(json.loads(str(m)))
        print("\n\n")
