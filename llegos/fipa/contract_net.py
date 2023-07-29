"""
https://en.m.wikipedia.org/wiki/Contract_Net_Protocol
http://www.fipa.org/specs/fipa00029/SC00029H.pdf
"""

from abc import ABC, abstractmethod

from llegos.asyncio import async_message_graph, async_propogate_all
from llegos.messages import Request, Response
from llegos.networks import AgentNetwork, Field, NetworkAgent

"""
First, we define our Message types.
"""


class CallForProposal(Request):
    intent = "call_for_proposal"
    objective: str = Field()
    desires: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class Refuse(Response):
    intent = "refuse"
    reason: str


class Propose(Response):
    intent = "propose"
    body: str


class AcceptProposal(Response):
    intent = "accept_proposal"


class RejectProposal(Response):
    intent = "reject_proposal"


class Failure(Response):
    intent = "failure"
    reason: str


class InformDone(Response):
    intent = "inform_done"


class InformResult(Response):
    intent = "inform_result"
    result: str


class Contractor(NetworkAgent, ABC):
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


class Delegator(NetworkAgent, ABC):
    @property
    def receptive_contractors(self):
        return self.receptive_agents(CallForProposal)

    @abstractmethod
    async def propose(self, message: Propose):
        """Receive a proposal and return an acceptance or a rejection"""

    @abstractmethod
    async def inform_done(self, message: InformDone):
        """Receive a message that the task is done"""

    @abstractmethod
    async def inform_result(self, message: InformResult):
        """Receive a message with the result of the task"""
        yield Response.forward(message, sender=self)

    @abstractmethod
    async def failure(self, message: Failure):
        """Receive a message that the task failed"""


class ContractNet(AgentNetwork):
    delegator: Delegator = Field(allow_mutation=False)
    contractors: list[Contractor] = Field(min_items=1, allow_mutation=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.graph.add_edges_from(
            (self.delegator, contractor, message)
            for contractor in self.contractors
            for message in contractor.receivable_messages
        )
        self.graph.add_edges_from(
            (contractor, self.delegator, message)
            for contractor in self.contractors
            for message in self.delegator.receivable_messages
        )

    async def request(self, message: Request):
        messages = [
            CallForProposal.forward(message, sender=self.delegator, receiver=c)
            for c in self.contractors
        ]
        await async_message_graph(async_propogate_all(messages))
