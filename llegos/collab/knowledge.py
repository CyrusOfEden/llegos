from llegos.ephemeral import EphemeralMessage, Field
from llegos.networks import ActorNetwork, NetworkActor


class Observation(EphemeralMessage):
    content: str


class Knowledge(EphemeralMessage):
    content: str


class Insight(Knowledge):
    ...


class LearningAgent(NetworkActor):
    def knowledge(self, message: Knowledge):
        ...

    def insight(self, message: Insight):
        ...


class GuidingAgent(LearningAgent):
    def observation(self, message: Observation):
        ...


class KnowledgeNetwork(ActorNetwork):
    guide: GuidingAgent
    learners: list[LearningAgent] = Field(min_items=1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for learner in enumerate(self.learners):
            self.graph.add_edge(self.guide, learner)

    def knowledge(self, k: Knowledge):
        return k.forward_to(self.guide)
