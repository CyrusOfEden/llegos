"""
https://en.m.wikipedia.org/wiki/Contract_Net_Protocol
"""

from pprint import pprint

from llm_net.gen import Field, GenAgent, Message


class Contractor(GenAgent):
    def call_for_proposal(self, message: Message) -> Message:
        """Manager requested a service from this agent."""
        accept = True
        content = "Yes" if accept else "No"
        if accept:
            return Message.reply(message, content, method="propose")
        else:
            return Message.reply(message, content, method="reject")

    def accept(self, message: Message) -> Message:
        """Manager accepted the proposal"""
        done = True
        content = "Done" if done else "Unable to complete task"
        if done:
            return Message.reply(message, content, method="inform")
        else:
            return Message.reply(message, content, method="cancel")

    def reject(self, message: Message):
        """Manager rejected the proposal."""
        # Update learnings about the manager
        # Update state


class Manager(GenAgent):
    contractors: list[Contractor] = Field(default_factory=list)
    results: list[Message] = Field(default_factory=list)

    def perform(self, message: Message):
        """Perform the ContractNet protocol"""
        responses = [c.call_for_proposal(message) for c in self.contractors]

        for r in responses:
            reply = self.receive(r)

        proposals = [r for r in responses if r.method == "propose"]

        # Set winning contractor to the first one
        winner: GenAgent = proposals[0].sender
        for p in proposals[1:]:
            agent: GenAgent = p.sender
            if agent is not winner:
                agent.receive(Message.reply(p, "No", method="reject"))

        reply = self.reply_to(p, "Your proposal has been accepted.", method="accept")
        result = winner.receive(reply)
        self.receive(result)

    def reject(self, message: Message):
        """Contractor rejected the proposal"""
        # Update learnings about the contractor
        # Update state

    def propose(self, message: Message):
        """Contractor proposes to complete the task."""
        # Update learnings about the contractor
        # Update state

    def inform(self, message: Message):
        """Contractor completed the task."""
        result = message
        proposal = result.reply_to
        task = proposal.reply_to
        print("TASK ======================================")
        pprint(task)
        print("PROPOSAL ==================================")
        pprint(proposal)
        print("RESULT ====================================")
        pprint(result)

        self.results.append(result)

    def cancel(self, message: Message):
        """Contractor was unable to fulfill the request."""
        # Update learnings about the contractor
        # Update state
        # Error handling?
