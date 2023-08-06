import json
from pprint import pprint

import pytest
from dotenv import load_dotenv

from llegos.collaborative.dialog import Dialog, DialogActor, DialogNetwork, StartDialog
from llegos.ephemeral import EphemeralMessage, Field
from llegos.functional import use_actor_message, use_gen_model, use_reply_to
from llegos.messages import Ack, Chat
from llegos.networks import Propogate
from llegos.test_helpers import MockCognition


class Quality(Ack):
    "Quality is good, no further refinement is needed."


class Consider(StartDialog):
    "Consider the material."


class Refine(Dialog):
    "Think, reason, and refine a response."
    thought: str = Field(include=True, description="think about how we can refine this")
    reasoning: str = Field(include=True, description="explain your reasoning")
    response: str = Field(include=True)


class RefiningActor(DialogActor):
    receivable_messages: set[type[EphemeralMessage]] = Field(
        default={Consider, Refine}, exclude=True
    )

    def consider(self, c: Consider) -> Refine:
        model_kwargs = use_gen_model(
            model="gpt-4-0613",
            max_tokens=4096,
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

        return function_call(completion)

    def refine(self, r: Refine):
        model_kwargs = use_gen_model(
            model="gpt-4-0613",
            max_tokens=4096,
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

        return function_call(completion)

    def chat(self, c: Chat):
        "Sometimes GPT returns an assistant Chat message, handle it here."


class Prompt(StartDialog):
    content: str = Field(include=True)


class PhilosophicalEnsemble(DialogNetwork):
    def prompt(self, message: Prompt):
        for agent in self.agents:
            yield Consider.forward(message, to=agent)


class TestDialogNetwork:
    @classmethod
    def setup_class(cls):
        load_dotenv()

    @pytest.mark.asyncio
    async def test_dialog_network(self):
        cognition = MockCognition()

        ensemble = PhilosophicalEnsemble(
            cognition=cognition,
            system="ensemble",
            agents={
                RefiningActor(cognition=cognition, system="Kieerkegard"),
                RefiningActor(cognition=cognition, system="Rumi"),
                RefiningActor(cognition=cognition, system="Laotzu"),
                RefiningActor(cognition=cognition, system="Buddha"),
                RefiningActor(cognition=cognition, system="Alan Watts"),
            },
        )

        question = Prompt(
            content="How can one channel love into the world?",
            receiver=ensemble,
        )
        message = Propogate(message=question)

        async for m in ensemble.receive(message):
            pprint(json.loads(str(m)))
            print("\n\n")
