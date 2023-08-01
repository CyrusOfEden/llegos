from llegos.ephemeral import EphemeralMessage, Field
from llegos.networks import AgentNetwork, NetworkAgent
from llegos.openai import OpenAIAgent


class Observation(EphemeralMessage):
    ...


class Knowledge(EphemeralMessage):
    content: str


class Insight(Knowledge):
    ...


class Learner(NetworkAgent, OpenAIAgent):
    async def knowledge(self, message: Knowledge):
        ...

    async def insight(self, message: Insight):
        ...


class Guide(Learner):
    async def observation(self, message: Observation):
        ...


class KnowledgeNetwork(AgentNetwork):
    guide: Guide
    learners: list[Learner] = Field(min_items=1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for learner in enumerate(self.learners):
            self.graph.add_edge(self.guide, learner)

    def knowledge(self, message: Knowledge):
        return message.forward_to(self.guide)
