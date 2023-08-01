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

import pytest

from llegos.collaborative.contract_net import (
    Accept,
    CallForProposal,
    ContractNet,
    Contractor,
    Failure,
    Manager,
    Propose,
    Reject,
    Request,
)


class InvariantError(TypeError):
    ...


class DemotivatedWorker(Contractor):
    async def call_for_proposal(self, message: CallForProposal) -> Reject:
        return Reject.reply_to(message, reason="I can't do it!")

    async def accept(self, message: Accept):
        raise InvariantError("should never be called")

    async def reject(self, message: Accept):
        raise InvariantError("should never be called")


class IncapableWorker(Contractor):
    async def call_for_proposal(self, message: CallForProposal) -> Propose:
        return Propose.reply_to(message, content="I believe I can do it!")

    async def accept(self, message: Accept) -> Failure:
        return Failure.reply_to(message)

    async def reject(self, message: Reject):
        raise InvariantError("should never be called")


class TestContractNet:
    @pytest.mark.asyncio
    async def xtest_receiving_response(self):
        ContractNet(
            manager=Manager(description=""),
            contractors=[
                Contractor(description=""),
                Contractor(description=""),
                Contractor(description=""),
                DemotivatedWorker(description=""),
                IncapableWorker(description=""),
            ],
        )

        Request(objective="", desires=[], requirements=[], constraints=[])
