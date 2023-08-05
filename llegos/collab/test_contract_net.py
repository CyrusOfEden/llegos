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

from llegos.collab.contract_net import (
    Accept,
    CallForProposal,
    Cancel,
    ContractNet,
    ContractorAgent,
    Inform,
    ManagerAgent,
    Propose,
    Reject,
    Request,
)
from llegos.openai import use_agent_message, use_messages
from llegos.test_helpers import MockCognition


class InvariantError(TypeError):
    ...


class WritingAgency(ManagerAgent):
    def request(self, message: Request):
        messages = use_messages(
            system=f"""\
            {self.description}
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

        function_kwargs, function_call = use_agent_message(
            {CallForProposal}, agents=self.available_contractors, sender=self
        )

        completion = self.cognition.language(
            model="gpt-4-0613", messages=messages, max_tokens=4096, **function_kwargs
        )

        return function_call(completion)

    def propose(self, message: Propose) -> Reject | CallForProposal | Accept:
        messages = use_messages(
            system=f"""\
            {self.description}
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

        function_kwargs, function_call = use_agent_message(
            {Accept, CallForProposal, Reject},
            agents=[message.sender],
            sender=self,
        )

        completion = self.cognition.language(
            model="gpt-4-0613",
            messages=messages,
            max_tokens=4096,
            **function_kwargs,
        )

        return function_call(completion)

    def inform(self, message: Inform):
        ...


class Subcontractor(ContractorAgent):
    def call_for_proposal(self, message: CallForProposal) -> Propose | Reject:
        messages = use_messages(
            system=f"""\
            {self.description}

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

        function_kwargs, function_call = use_agent_message(
            {Propose, Reject},
            agents=[message.sender],
            sender=self,
        )

        completion = self.cognition.language(
            model="gpt-4-0613",
            messages=messages,
            max_tokens=4096,
            **function_kwargs,
        )

        return function_call(completion)

    def accept(self, message: Accept) -> Inform | Cancel:
        messages = use_messages(
            system="""\
            {self.description}

            Below is the conversation history between an outliner and a writer.
            """,
            context=message,
            context_history=8,
            prompt="""\
            Inform with the generated content.
            """,
        )

        function_kwargs, function_call = use_agent_message(
            {Inform, Cancel},
            agents=[message.sender],
            sender=self,
        )

        completion = self.cognition.language(
            model="gpt-4-0613",
            messages=messages,
            max_tokens=4096,
            **function_kwargs,
        )

        return function_call(completion)


class DemotivatedWriter(ContractorAgent):
    """
    This agent is demotivated and will reject any task.
    """

    def call_for_proposal(self, message: CallForProposal) -> Reject:
        return Reject.reply_to(message, reason="I can't do it!")

    def accept(self, _: Accept):
        raise InvariantError("should never be called")

    def reject(self, _: Accept):
        raise InvariantError("should never be called")


class IncapableWriter(ContractorAgent):
    """
    This agent accepts all tasks, despite always being incapable of doing them.
    """

    def call_for_proposal(self, message: CallForProposal) -> Propose:
        return Propose.reply_to(
            message, plan="I believe I can do it, but I have no plan!"
        )

    def accept(self, message: Accept) -> Cancel:
        return Cancel.reply_to(message)

    def reject(self, _: Reject):
        raise InvariantError("should never be called")


class TestContractNet:
    @classmethod
    def setup_class(cls):
        load_dotenv()

    @pytest.mark.asyncio
    async def test_receiving_response(self):
        cognition = MockCognition()

        network = ContractNet(
            description="Contract Net",
            manager=WritingAgency(
                cognition=cognition,
                description="An expert technical writer and outliner.",
            ),
            contractors=[
                # one of these contractors will ultimately do this task
                Subcontractor(
                    cognition=cognition,
                    description="""\
                    You are engaging and great at explaining things
                    in an understandable way by the general population.
                    """,
                ),
                Subcontractor(
                    cognition=cognition,
                    description="""\
                    You are an expert in computer science and programming,
                    able to explain technical concepts concisely and precisely.
                    """,
                ),
                # the failing workers are put first to demonstrate contract net's ability to recover
                DemotivatedWriter(),
                IncapableWriter(),
            ],
        )

        request = Request(
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
            receiver=network,
        )

        async for m in network.propogate(request):
            pprint(m.dict())
            print("\n\n")
