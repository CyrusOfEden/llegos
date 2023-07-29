"""
https://en.m.wikipedia.org/wiki/Contract_Net_Protocol
http://www.fipa.org/specs/fipa00029/SC00029H.pdf
"""

from abc import ABC, abstractmethod
from typing import AsyncIterable

from statemachine import StateMachine

from llegos.asyncio import async_propogate_all
from llegos.networks import AgentNetwork, EphemeralMessage, Field, NetworkAgent

"""
First, we define our Message types.
"""


class CallForProposal(EphemeralMessage):
    intent = "call_for_proposal"
    objective: str = Field()
    constraints: list[str] = Field()


class Refuse(EphemeralMessage):
    intent = "refuse"


class Propose(EphemeralMessage):
    intent = "propose"


class AcceptProposal(EphemeralMessage):
    intent = "accept_proposal"


class RejectProposal(EphemeralMessage):
    intent = "reject_proposal"


class Failure(EphemeralMessage):
    intent = "failure"


class InformDone(EphemeralMessage):
    intent = "inform_done"


class InformResult(EphemeralMessage):
    intent = "inform_result"


class Request(EphemeralMessage):
    intent = "request"


class Response(EphemeralMessage):
    intent = "response"


class Participant(NetworkAgent, StateMachine, ABC):
    """
    An abstract base class for a contract net participant, i.e. a contractor meant to
    receive a CFP, respond with a proposal, and then perform the task if their proposal
    was approved.
    """

    receivable_messages = {CallForProposal, RejectProposal, AcceptProposal}

    @abstractmethod
    async def call_for_proposal(self, message: CallForProposal) -> Propose | Refuse:
        """Receive a call for a proposal and return a proposal or a refusal"""
        ...

    @abstractmethod
    async def accept_proposal(
        self, message: AcceptProposal
    ) -> InformDone | InformResult | Failure:
        """Receive an accepted proposal and perform the task"""
        ...

    @abstractmethod
    async def reject_proposal(self, message: RejectProposal) -> None:
        """Receive a rejected proposal and process it"""
        ...


class Initiator(NetworkAgent, StateMachine, ABC):
    receivable_messages = {Propose, Refuse, InformDone, InformResult, Failure}

    @abstractmethod
    async def propose(self, message: Propose):
        """Receive a proposal and return an acceptance or a rejection"""

    @abstractmethod
    async def inform_done(self, message: InformDone):
        """Receive a message that the task is done"""
        ...

    @abstractmethod
    async def inform_result(self, message: InformResult):
        """Receive a message with the result of the task"""
        yield Response.forward(message, sender=self)

    @abstractmethod
    async def failure(self, message: Failure):
        """Receive a message that the task failed"""
        ...


ContractNetMessage = (
    CallForProposal | Refuse | Propose | AcceptProposal | RejectProposal
)


class ContractNet(AgentNetwork):
    manager: Initiator = Field(allow_mutation=False)
    contractors: list[Participant] = Field(min_items=1, allow_mutation=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.graph.add_edges_from(
            (self.manager, contractor, message)
            for contractor in self.contractors
            for message in contractor.receivable_messages
        )
        self.graph.add_edges_from(
            (contractor, self.manager, message)
            for contractor in self.contractors
            for message in self.manager.receivable_messages
        )

    async def request(self, message: Request) -> AsyncIterable[ContractNetMessage]:
        messages = [
            CallForProposal.forward(message, sender=self.manager, receiver=c)
            for c in self.contractors
        ]
        async for reply in async_propogate_all(messages):
            yield reply
