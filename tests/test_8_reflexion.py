"""
https://github.com/noahshinn/reflexion
"""

from pydantic import Field

from llegos import research as llegos


class Action(llegos.Message):
    text: str


class Observation(llegos.Message):
    text: str


class Reward(llegos.Message):
    value: float


class Feedback(llegos.Message):
    text: str


class Trajectory(llegos.Object):
    """
    Short-term memories
    """

    memories: list[str] = Field(default_factory=list)


class Experience(llegos.Object):
    """
    Long-term memories
    """

    memories: list[str] = Field(default_factory=list)


class EvaluatorLM(llegos.Actor):
    trajectory: Trajectory


class ActorLM(llegos.Actor):
    trajectory: Trajectory
    experience: Experience


class SelfReflectionLM(llegos.Actor):
    experience: Experience

    def receive_feedback(self, feedback: Feedback):
        self.experience.memories.append(feedback.text)


class Agent(llegos.Actor):
    actor: ActorLM
    evaluator: EvaluatorLM
    self_reflection: SelfReflectionLM
