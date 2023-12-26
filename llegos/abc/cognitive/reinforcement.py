from abc import ABC, abstractmethod
from operator import itemgetter

from beartype.typing import AsyncIterable
from networkx import DiGraph

from llegos.research import Actor, Field, Message, message_path


class Percept(Message):
    ...


class PerceptionBehavior(Actor, ABC):
    ...


class Action(Message):
    ...


class Cost(Message):
    value: float = Field(gte=0)


class CostBehavior(Actor, ABC):
    _loss_landscape: DiGraph = Field(default_factory=DiGraph)

    @abstractmethod
    def forward(self, predicted_step: Percept) -> Cost:
        action: Action = predicted_step.parent
        previous_step: Percept = action.parent
        loss = Cost.reply_to(action, value=0)

        self.loss_landscape.add_edge(previous_step, predicted_step, weight=loss.value)

        return loss

    @abstractmethod
    def backward(self, realized_step: Percept) -> Cost:
        action: Action = realized_step.parent

        edge = self.loss_landscape[action][realized_step]
        predicted_loss = edge["weight"]
        actual_loss = 0

        edge["weight"] = actual_loss
        edge["error"] = predicted_loss - actual_loss

        return Cost.reply_to(realized_step, value=actual_loss)


class Reward(Message):
    value: float = Field(default=0)


class RewardBehavior(Actor, ABC):
    reward_path: DiGraph = Field(default_factory=DiGraph, include=False, exclude=True)

    @abstractmethod
    def forward(self, message: Cost) -> Reward:
        reward = Reward.reply_to(message, value=0)

        if (gen := message.parent) and (re := gen.parent):
            self.reward_path.add_weighted_edges_from([(re, gen, reward.value)])

        return reward

    @abstractmethod
    def backward(self, message: Cost) -> Reward:
        reward = Reward.reply_to(message, value=1)

        if (gen := message.parent) and (re := gen.parent):
            self.reward_path.add_weighted_edges_from([(re, gen, reward.value)])

        return reward


class ActionBehavior(Actor, ABC):
    @abstractmethod
    def forward(self, current_step: Percept) -> AsyncIterable[Action]:
        "Predict possible actions from a given step."

    @abstractmethod
    def backward(self, realized_step: Percept):
        "Update the model based on the material step."


class WorldModelBehavior(Actor, ABC):
    @abstractmethod
    def forward(self, action: Action) -> Percept:
        "Predict the next step of the world based on the action."

    @abstractmethod
    def backward(self, realized_step: Percept):
        "Update the model based on the material step."


class ExecutiveBehavior(Actor, ABC):
    _cost: CostBehavior
    _reward: RewardBehavior
    _action: ActionBehavior
    _world_model: WorldModelBehavior

    def forward(self, step: Percept, action_lookahead: int) -> Action:
        if action_lookahead <= 0:
            raise ValueError("search_depth must be greater than 0")

        future_actions: list[tuple[Action, float]] = []

        prior_cost = self._cost.forward(step)
        prior_reward = self._reward.forward(prior_cost)

        predictions: list[Percept] = []
        for action in self._action.forward(prior_reward):
            predicted_step = self._world_model.forward(action)
            predictions.append(predicted_step)
            predicted_loss = self._cost.forward(predicted_step)

            foresight = (action, predicted_loss.value)
            future_actions.append(foresight)

        action = sorted(future_actions, key=itemgetter(1))[0][0]
        if action_lookahead == 1:
            return action

        if not predictions:
            raise ValueError("No predictions were made.")

        final_action = self.forward(predictions[-1], action_lookahead - 1)
        predictions = message_path(step, final_action)
        next_action = next(p for p in predictions if isinstance(p, Action))
        return next_action

    def backward(self, step: Percept):
        loss = self._cost.backward(step)
        reward = self._reward.backward(loss)
        self._action.backward(reward)
        self._world_model.backward(reward)
