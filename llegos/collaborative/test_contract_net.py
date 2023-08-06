"""
Contract Net is a task-sharing protocol developed by Reid G. Smith in 1980.

This protocol can be used to implement hierarchical organizations, where a manager
assigns tasks to contractors, who in turn decompose into lower level task and
assign them to the lower level. This kind of organization can be used when agents
are cooperative, i.e. when their objectives are identical. In this situation, it is
possible to make sure that the contractors do not lie to the manager when they make
their proposal. When the agents are competitive, the protocol ends up in a marketplace
organization, very similar to auctions.

It was standardized by the Foundation for Intelligent Physical Agents as a multi-agent
communication protocol.

https://en.m.wikipedia.org/wiki/Contract_Net_Protocol
"""

from pprint import pprint
from textwrap import dedent

import pytest
from dotenv import load_dotenv

from llegos.collaborative.contract_net import (
    Accept,
    CallForProposal,
    Cancel,
    ContractNet,
    ContractorActor,
    Inform,
    ManagerActor,
    Propose,
    Reject,
    Request,
)
from llegos.functional import use_actor_message, use_gen_model, use_reply_to
from llegos.networks import Propogate
from llegos.test_helpers import MockCognition


class InvariantError(TypeError):
    ...


class WritingManager(ManagerActor):
    def request(self, message: Request):
        model_kwargs = use_gen_model(
            model="gpt-4-0613",
            max_tokens=4096,
            # these are special llegos params that are used to generate a list[dict] of messages
            system=f"""\
            {self.system}
            """,
            context=message,
            context_history=8,
            prompt="""\
            First, think quietly about what the first task should be.
            Then, think quietly about which contractor is best suited for it.
            Finally, issue the task to that contractor.
            Make the decision, do not seek approval.
            The generated JSON MUST BE in the function_call key, not the content.
            """,
        )

        function_kwargs, function_call = use_actor_message(
            self.receivers(CallForProposal),
            messages={CallForProposal},
            sender=self,
            parent=message,
        )

        completion = self.cognition.language(**model_kwargs, **function_kwargs)

        return function_call(completion)

    def propose(self, message: Propose) -> Reject | CallForProposal | Accept:
        model_args = use_gen_model(
            model="gpt-4-0613",
            max_tokens=4096,
            system=f"""\
            {self.system}
            """,
            context=message,
            context_history=4,
            prompt="""\
            First, review the proposed plan and analyze it.
            If you are satisfied with the plan, Accept the plan.
            If you think the plan can be improved, Call for a Proposal.
            If you are not satisfied with the plan, Reject the plan.
            Make the decision, do not seek approval.
            The generated JSON MUST BE in the function_call key, not the content.
            """,
        )

        function_kwargs, function_call = use_reply_to(
            message,
            {Accept, CallForProposal, Reject},
        )

        completion = self.cognition.language(**model_args, **function_kwargs)

        return function_call(completion)

    def inform(self, message: Inform):
        return Inform.forward(message, to=self.network)

    def reject(self, message: Reject):
        ...

    def cancel(self, message: Cancel):
        ...


class WritingContractor(ContractorActor):
    def call_for_proposal(self, message: CallForProposal) -> Propose | Reject:
        model_kwargs = use_gen_model(
            model="gpt-4-0613",
            max_tokens=4096,
            system=f"""\
            {self.system}

            YOU MUST THINK QUIETLY.
            """,
            context=message,
            context_history=8,
            prompt="""\
            First, think quietly about a plan to complete the task.
            Then, think quietly whether your plan is a good plan.
            If it is a good plan, Propose the plan.
            Otherwise, Reject the task and explain why.
            """,
        )

        function_kwargs, function_call = use_reply_to(
            message,
            {Propose, Reject},
        )

        completion = self.cognition.language(**model_kwargs, **function_kwargs)

        return function_call(completion)

    def accept(self, message: Accept) -> Inform | Cancel:
        model_kwargs = use_gen_model(
            model="gpt-4-0613",
            max_tokens=4096,
            system=self.system,
            context=message,
            context_history=8,
            prompt=f"Imagine {self.id} informing {message.sender_id} with generated content.",
        )

        function_kwargs, function_call = use_reply_to(
            message,
            {Inform, Cancel},
        )

        completion = self.cognition.language(**model_kwargs, **function_kwargs)

        return function_call(completion)

    def reject(self, message: Reject):
        ...


class WritingAgency(ContractNet):
    def request(self, message: Request):
        return Request.forward(message, to=self.manager)


class TestContractNet:
    @classmethod
    def setup_class(cls):
        load_dotenv()

    @pytest.mark.asyncio
    async def test_receiving_response(self):
        cognition = MockCognition()

        network = WritingAgency(
            system="Writing Agency",
            manager=WritingManager(
                cognition=cognition,
                system="Writing manager",
            ),
            contractors=[
                # one of these contractors will ultimately do this task
                WritingContractor(
                    cognition=cognition,
                    system="""\
                    You are engaging and great at explaining things
                    in an understandable way by the general population.
                    """,
                ),
                WritingContractor(
                    cognition=cognition,
                    system="""\
                    You are an expert in computer science and programming,
                    able to explain technical concepts concisely and precisely.
                    """,
                ),
            ],
        )

        request = Request(
            receiver=network,
            objective=dedent(
                """\
                Write a piece comparing the message-passing of biological cells
                to message-passing in multi-agent networks.
                """
            ),
            requirements=[
                "Engaging",
                "Intuitive",
                "Concise",
                "Precise",
            ],
        )

        async for m in network.receive(Propogate(message=request)):
            pprint(m.dict())
            print("\n\n")
