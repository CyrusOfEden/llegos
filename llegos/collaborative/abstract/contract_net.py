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

This implements the Iterative Contract Net protocol as depicted in this diagram:
https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Icnp.svg/880px-Icnp.svg.png
"""


from abc import ABC, abstractmethod

from llegos.contexts import Context, ContextualRole, Field
from llegos.messages import EphemeralMessage, find_closest


class Request(EphemeralMessage):
    "A request for a particular objective to be achieved with some requirements and constraints"
    objective: str = Field(include=True)
    requirements: list[str] = Field(default_factory=list, include=True)
    constraints: list[str] = Field(default_factory=list, include=True)


class CallForProposal(Request):
    "Pass off a particular task to a contractor, include the context of the Request"
    task: str = Field(include=True)


class Reject(EphemeralMessage):
    "Reject a request with a reason"
    reason: str = Field(include=True)
    feedback: str = Field(include=True)


class Propose(EphemeralMessage):
    "Propose a plan to achieve the objective with the requirements and constraints"
    plan: str = Field(include=True)


class Accept(EphemeralMessage):
    "Accept the proposal from the contractor"
    feedback: str = Field(include=True)


class Cancel(EphemeralMessage):
    "Notify the manager that the task has been cancelled"
    reason: str = Field(include=True)


class Inform(EphemeralMessage):
    "Inform the manager that the task has been completed"
    content: str = Field(include=True)


class Response(EphemeralMessage):
    "Response from the ephemeral network"
    content: str = Field(include=True)


class ContractorRole(ContextualRole):
    receivable_messages: set[type[EphemeralMessage]] = Field(
        default={
            CallForProposal,
            Accept,
            Reject,
        },
        exclude=True,
    )

    async def call_for_proposal(self, message: CallForProposal) -> Propose | Reject:
        accept = True
        if accept:
            return Propose.reply_to(message, body="I can do it")
        else:
            return Reject.reply_to(message, reason="I can't do it")

    async def accept(self, message: Accept) -> Inform | Cancel:
        try:
            # Do the work
            return Inform.reply_to(message, result="I did it!")
        except Exception as e:
            return Cancel.reply_to(message, reason=str(e))

    async def reject(self, message: Reject):
        ...


class ManagerRole(ContextualRole, ABC):
    receivable_messages: set[type[EphemeralMessage]] = Field(
        default={
            Request,
            Propose,
            Reject,
            Inform,
            Cancel,
        },
        exclude=True,
    )

    @abstractmethod
    def request(self, message: Request):
        ...

    @abstractmethod
    def propose(self, message: Propose) -> Reject | CallForProposal | Accept:
        ...

    def reject(self, result: Reject):
        ...

    @abstractmethod
    def inform(self, result: Inform):
        ...

    def cancel(self, cancel: Cancel):
        ...


class ContractNet(Context):
    manager: ManagerRole = Field()
    contractors: list[ContractorRole] = Field(min_items=2)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.graph.add_edge(self, self.manager)
        for priority, contractor in enumerate(self.contractors):
            self.graph.add_edge(self.manager, contractor, weight=priority)

    def request(self, req: Request):
        return Request.forward(req, to=self.manager, sender=self)

    def inform(self, message: Inform):
        request = find_closest(Request, of_message=message)
        return Response.forward(message, to=request.sender)
