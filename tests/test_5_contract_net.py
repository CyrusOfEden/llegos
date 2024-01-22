"""
This example is meant to highlight how easy it is to go from a waterfall diagram
to a working implementation with llegos.

We are going to implement the Iterative Contract Net protocol as depicted in this diagram:
https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Icnp.svg/880px-Icnp.svg.png

Contract Net is a task-sharing protocol developed by Reid G. Smith in 1980. It was standardized
by the Foundation for Intelligent Physical Agents as a multi-agent communication protocol.

Learn more about it here: https://en.m.wikipedia.org/wiki/Contract_Net_Protocol
"""

from typing import Sequence

from matchref import ref
from pydantic import BaseModel

from llegos import research as llegos

"""
The first step is to define the messages that will be passed between the actors.
We look at the chart, and for every arrow, we define a message.

These messages are fully typed pydantic models, so we can make them as complex as required.

It's recommended you use a library like Instructor or Outlines to generate these with an LLM.
"""


class CallForProposal(llegos.Message):
    task: str


class Reject(llegos.Message):
    reason: str


class Step(BaseModel):
    id: int
    action: str


class Propose(llegos.Message):
    "Propose a plan to achieve the objective with the requirements and constraints"
    plan: list[Step]


class Accept(llegos.Message):
    "Accept the proposal from the contractor"
    feedback: str


class Cancel(llegos.Message):
    "Notify the manager that the task has been cancelled"
    reason: str


class Inform(llegos.Message):
    "Inform the manager that the task has been completed"
    content: str


class Response(llegos.Message):
    "Response from the ephemeral network"
    content: str


"""
Now we're going to implement the actors. Let's start with the Contractor.

For every message that has an arrow pointing to the contractor, we define a method
called `receive_<camel_case_message_name)>`. This method will be called when the
contractor receives a message of that type.
"""


class Contractor(llegos.Actor):
    """
    In reality you'd generate the plan based on the task,
    but for this example, we'll just hard-code it.
    """

    plan: list[Step]

    def receive_call_for_proposal(self, message: CallForProposal) -> Propose | Reject:
        return Propose.reply_to(message, plan=self.plan)

    def receive_accept(self, message: Accept) -> Inform | Cancel:
        return Inform.reply_to(message, content="The answer is 42")

    def receive_reject(self, message: Reject):
        """
        This would be a good opportunity to do some reflection.
        """


class Manager(llegos.Actor):
    """
    Sometimes you don't need to support 1 actor existing in multiple networks.
    In that case, you can just store references to the relevant actors (contractors here).
    """

    contractors: Sequence[llegos.Actor]

    def receive_call_for_proposal(self, message: CallForProposal) -> Propose | Reject:
        """
        First, we gather all actors in the network that can receive the CallForProposal message
        """
        for c in self.contractors:
            """
            Here we yield the different messages we want to send to the contractors.
            Why? Because when we yield, it stops the execution of this method, yields
            the message, the message will be sent to the contractor, the interaction
            will follow, until there are no more messages to send, then we'll continue
            to yield the next message to the next contractor, and so on.

            The caller can then iterate on the generated messages until an `Inform` message
            is yielded, and then stop the iteration and return the message to its caller.
            """
            yield message.forward_to(c)
        else:
            """
            If the caller iterates on the generator until it's exhausted, then we know
            that no contractor was available to receive the message, so we return a Reject
            message to the caller.
            """
            return Reject.reply_to(message, reason="No contractors available")

    def receive_propose(self, message: Propose) -> Reject | CallForProposal | Accept:
        match len(message.plan):
            case 1:
                return Reject.reply_to(message, reason="I don't like it")
            case 2:
                return CallForProposal.reply_to(message, task="do something else")
            case 3:
                return Accept.reply_to(message, feedback="Sounds good")

    def receive_accept(self, message: Accept) -> Inform | Cancel:
        """
        Find the closest message of type Propose in the ancestors.
        """
        proposal = next(
            m
            for m in llegos.message_ancestors(message)
            if isinstance(m, Propose) and message.receiver == self
        )
        return message.forward_to(proposal.sender)

    def receive_reject(self, result: Reject):
        ...

    def receive_inform(self, result: Inform):
        call_for_proposal = next(
            m
            for m in llegos.message_ancestors(result)
            if isinstance(m, CallForProposal) and m.receiver == self
        )
        return result.forward_to(call_for_proposal.sender)

    def receive_cancel(self, cancel: Cancel):
        ...


def test_contract_net():
    user = llegos.Actor()  # a simple, dummy actor with no utility
    manager = Manager(
        contractors=[
            Contractor(plan=[Step(id=1, action="do the thing")]),
            Contractor(
                plan=[
                    Step(id=1, action="do the thing"),
                    Step(id=2, action="do the other thing"),
                ]
            ),
            Contractor(
                plan=[
                    Step(id=1, action="do the other thing"),
                    Step(id=2, action="do the thing"),
                    Step(id=3, action="tell you about it"),
                ]
            ),
        ]
    )

    req = CallForProposal(
        sender=user,
        receiver=manager,
        task="do the thing",
    )

    """
    We can use matchref to match on the reference of the actor that sent the message.
    """
    for msg in llegos.message_propagate(req):
        """
        message_propagate that keeps calling message_send on yielded messages.
        """
        match msg:
            case Inform(sender=ref.manager, receiver=ref.user):
                assert msg.content == "The answer is 42"
                break


def test_nested_contract_net():
    user = llegos.Actor()  # a simple, dummy actor with no utility
    manager = Manager(
        contractors=[
            Contractor(plan=[Step(id=1, action="do the thing")]),
            Contractor(
                plan=[
                    Step(id=1, action="do the thing"),
                    Step(id=2, action="do the other thing"),
                ]
            ),
            Manager(
                contractors=[
                    Contractor(plan=[Step(id=1, action="do the thing")]),
                    Contractor(
                        plan=[
                            Step(id=1, action="do the other thing"),
                            Step(id=2, action="do the thing"),
                            Step(id=3, action="tell you about it"),
                        ]
                    ),
                ]
            ),
        ]
    )

    req = CallForProposal(
        sender=user,
        receiver=manager,
        task="do the thing",
    )

    for msg in llegos.message_propagate(req):
        """
        message_propagate that keeps calling message_send on yielded messages.
        """
        match msg:
            case Inform(receiver=ref.user, sender=ref.manager):
                """
                This is the Inform message returned to the user.
                """
                assert msg.content == "The answer is 42"
                break
            case Reject(receiver=ref.user):
                """
                This is the Reject message returned to the user.
                """
                assert msg.reason == "No contractors available"
                break
