from llegos.research import ContextualActor, Field, Message, Scene


class Observation(Message):
    content: str


class Knowledge(Message):
    content: str


class Insight(Knowledge):
    ...


class LearningAgent(ContextualActor):
    def knowledge(self, message: Knowledge):
        ...

    def insight(self, message: Insight):
        ...


class GuidingAgent(LearningAgent):
    def observation(self, message: Observation):
        ...


class KnowledgeContext(Scene):
    guide: GuidingAgent
    learners: list[LearningAgent] = Field(min_items=1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for learner in enumerate(self.learners):
            self.graph.add_edge(self.guide, learner)

    def knowledge(self, k: Knowledge):
        return k.forward_to(self.guide)
