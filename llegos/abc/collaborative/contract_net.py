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

from pydantic import BaseModel

from llegos.research import Actor, Field, Message, Scene, message_ancestor


class Request(Message):
    "A request for a particular objective to be achieved with some requirements and constraints"
    objective: str
    requirements: list[str] = Field(default_factory=list, include=True)
    constraints: list[str] = Field(default_factory=list, include=True)


class CallForProposal(Request):
    "Pass off a particular task to a contractor, include the context of the Request"
    task: str


class Reject(Message):
    "Reject a request with a reason"
    reason: str
    feedback: str


class Step(BaseModel):
    id: int
    action: str
    dependencies: list[int] = Field(
        description="A list of step ids that must be completed before this step can be started"
    )


class Propose(Message):
    "Propose a plan to achieve the objective with the requirements and constraints"
    plan: list[Step]


class Accept(Message):
    "Accept the proposal from the contractor"
    feedback: str


class Cancel(Message):
    "Notify the manager that the task has been cancelled"
    reason: str


class Inform(Message):
    "Inform the manager that the task has been completed"
    content: str


class Response(Message):
    "Response from the ephemeral network"
    content: str


class ContractorActor(Actor):
    _receivable_messages: set[type[Message]] = Field(
        default={
            CallForProposal,
            Accept,
            Reject,
        },
    )

    @abstractmethod
    async def call_for_proposal(self, message: CallForProposal) -> Propose | Reject:
        ...

    @abstractmethod
    async def handle_accept(self, message: Accept) -> Inform | Cancel:
        ...

    @abstractmethod
    async def reject(self, message: Reject):
        ...


class ManagerActor(Actor, ABC):
    _receivable_messages: set[type[Message]] = Field(
        default={
            Request,
            Propose,
            Reject,
            Inform,
            Cancel,
        }
    )

    @abstractmethod
    def handle_request(self, message: Request):
        ...

    @abstractmethod
    def handle_propose(self, message: Propose) -> Reject | CallForProposal | Accept:
        ...

    def handle_reject(self, result: Reject):
        ...

    @abstractmethod
    def handle_inform(self, result: Inform):
        ...

    def handle_cancel(self, cancel: Cancel):
        ...


class ContractNet(Scene):
    manager: ManagerActor = Field()
    contractors: list[ContractorActor] = Field(min_items=2)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._graph.add_edge(self, self.manager)
        for priority, contractor in enumerate(self.contractors):
            self._graph.add_edge(self.manager, contractor, weight=priority)

    def handle_request(self, req: Request):
        return Request.forward(req, receiver=self.manager, sender=self)

    def handle_inform(self, message: Inform):
        request = message_ancestor(Request, of_message=message)
        return Response.forward(message, receiver=request.sender)
