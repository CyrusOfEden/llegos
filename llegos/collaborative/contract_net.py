"""
Implements the Iterative Contract Net protocol as depicted in this diagram:
https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Icnp.svg/880px-Icnp.svg.png
"""


from llegos.messages import EphemeralMessage, SystemMessage, UserMessage, find_closest
from llegos.networks import AgentNetwork, Field, NetworkAgent
from llegos.openai import OpenAIAgent, prepare_functions, prepare_messages


class Request(EphemeralMessage):
    objective: str = Field()
    desires: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class CallForProposal(Request):
    ...


class Reject(EphemeralMessage):
    reason: str


class Propose(EphemeralMessage):
    plan: str


class Accept(EphemeralMessage):
    ...


class Failure(EphemeralMessage):
    reason: str


class Inform(EphemeralMessage):
    result: str


class Response(EphemeralMessage):
    result: str


class Contractor(OpenAIAgent, NetworkAgent):
    async def call_for_proposal(self, message: CallForProposal) -> Propose | Reject:
        accept = True
        if accept:
            return Propose.reply_to(message, body="I can do it")
        else:
            return Reject.reply_to(message, reason="I can't do it")

    async def accept(self, message: Accept) -> Inform | Failure:
        try:
            return Inform.reply_to(message, result="I did it!")
        except Exception as e:
            return Failure.reply_to(message, reason=str(e))

    async def reject(self, message: Reject) -> None:
        ...


class Manager(OpenAIAgent, NetworkAgent):
    @property
    def receptive_contractors(self):
        return self.receptive_agents(CallForProposal)

    async def request(self, message: Request):
        for contractor in self.receptive_contractors:
            yield CallForProposal.forward(message, to=contractor)

    async def propose(self, message: Propose) -> Reject | Propose | Accept:
        functions, function_call = prepare_functions(
            [Accept, CallForProposal, Reject],
        )

        messages = prepare_messages(
            system=SystemMessage(""), prompt=UserMessage.reply_to(message, content="")
        )

        completion = await self.completion.acreate(
            functions=functions, messages=messages
        )

        return function_call(completion)

    async def inform(self, result: Inform):
        yield Inform.forward(result, to=self.network)

    async def failure(self, failure: Failure):
        yield Failure.forward(failure, to=self.network)


class ContractNet(AgentNetwork):
    manager: Manager = Field()
    contractors: list[Contractor] = Field(min_items=2)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for priority, contractor in enumerate(self.contractors):
            self.graph.add_edge(self.manager, contractor, weight=priority)

    async def request(self, task: Request):
        return task.forward_to(self.manager)

    async def inform(self, result: Inform):
        request = find_closest(Request, of_message=result)
        return Response.forward(result, to=request.sender)
