"""
https://en.m.wikipedia.org/wiki/Contract_Net_Protocol
http://www.fipa.org/specs/fipa00029/SC00029H.pdf
"""

from abc import ABC, abstractmethod
from typing import AsyncIterable

from llegos.asyncio import async_propogate_all
from llegos.messages import message_chain
from llegos.networks import AgentNetwork, EphemeralMessage, Field, NetworkAgent
from llegos.openai import prepare_async_call

"""
First, we define our Message types.
"""


class CFP(EphemeralMessage):
    intent = "cfp"
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


"""
Then, onto the agents!
"""


class Participant(NetworkAgent, ABC):
    """
    An abstract base class for a contract net participant, i.e. a contractor meant to
    receive a CFP, respond with a proposal, and then perform the task if their proposal
    was approved.
    """

    receivable_messages = {CFP, RejectProposal, AcceptProposal, Failure}

    @abstractmethod
    async def cfp(self, message: CFP) -> Propose | Refuse:
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


class Initiator(NetworkAgent, ABC):
    receivable_messages = {Propose, Refuse, InformDone, InformResult, Failure}

    @abstractmethod
    async def propose(self, message: Propose):
        """Receive a proposal and return an acceptance or a rejection"""
        messages, functions, call_function = prepare_async_call(
            message_chain(message, height=12),
            llegos=[AcceptProposal, RejectProposal],
        )

        completion = self.completion.create(
            messages=messages, functions=functions, temperature=0.8, max_tokens=250
        )

        async for reply in call_function(completion):
            yield reply  # reply is either AcceptProposal or RejectProposal

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


ContractNetMessage = CFP | Refuse | Propose | AcceptProposal | RejectProposal


class ContractNet(AgentNetwork):
    manager: Initiator = Field()
    contractors: list[Participant] = Field(min_items=1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        [
            (self.manager, contractor.receivable_messages, contractor)
            for contractor in self.contractors
        ]

    async def request(self, message: Request) -> AsyncIterable[ContractNetMessage]:
        messages = [
            CFP.forward(message, sender=self.manager, receiver=c)
            for c in self.contractors
        ]
        async for reply in async_propogate_all(messages):
            yield reply
