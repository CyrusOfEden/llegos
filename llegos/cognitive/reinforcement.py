from abc import ABC, abstractmethod
from operator import itemgetter

from beartype.typing import AsyncIterable
from networkx import DiGraph

from llegos.research import Actor, Field, Message, find_closest, message_path


class Percept(Message):
    ...


class PerceptionBehavior(Actor, ABC):
    ...


class Action(Message):
    ...


class Cost(Message):
    value: float = Field(gte=0)


class CostBehavior(Actor, ABC):
    loss_landscape: DiGraph = Field(
        default_factory=DiGraph, include=False, exclude=True
    )

    @abstractmethod
    async def forward(self, predicted_step: Percept) -> Cost:
        action: Action = predicted_step.parent
        previous_step: Percept = action.parent
        loss = Cost.reply_to(action, value=0)

        self.loss_landscape.add_edge(previous_step, predicted_step, weight=loss.value)

        return loss

    @abstractmethod
    async def backward(self, realized_step: Percept) -> Cost:
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
    async def forward(self, message: Cost) -> Reward:
        reward = Reward.reply_to(message, value=0)

        gen = message.parent
        re = gen.parent
        self.reward_path.add_weighted_edges_from([(re, gen, reward.value)])

        return reward

    @abstractmethod
    async def backward(self, message: Cost) -> Reward:
        reward = Reward.reply_to(message, value=1)

        gen = message.parent
        re = gen.parent
        self.reward_path.add_weighted_edges_from([(re, gen, reward.value)])

        return reward


class ActionBehavior(Actor, ABC):
    @abstractmethod
    async def forward(self, current_step: Percept) -> AsyncIterable[Action]:
        "Predict possible actions from a given step."
        yield Action.reply_to(current_step, text="Possible Action #1")
        yield Action.reply_to(current_step, text="Possible Action #2")
        yield Action.reply_to(current_step, text="Possible Action #3")

    @abstractmethod
    async def backward(self, realized_step: Percept):
        "Update the model based on the material step."
        ...


class WorldModelBehavior(Actor, ABC):
    @abstractmethod
    async def forward(self, action: Action) -> Percept:
        "Predict the next step of the world based on the action."
        predicted_step = Percept.reply_to(action)
        return predicted_step

    @abstractmethod
    async def backward(self, realized_step: Percept):
        "Update the model based on the material step."
        find_closest(realized_step, Action)


class ExecutiveBehavior(Actor, ABC):
    cost: CostBehavior = Field(exclude=True)
    reward: RewardBehavior = Field(exclude=True)
    action: ActionBehavior = Field(exclude=True)
    world_model: WorldModelBehavior = Field(exclude=True)

    async def forward(self, step: Percept, action_lookahead: int) -> Action:
        if action_lookahead <= 0:
            raise ValueError("search_depth must be greater than 0")

        future_actions: list[tuple[Action, float]] = []

        prior_cost = await self.cost.forward(step)
        prior_reward = await self.reward.forward(prior_cost)

        async for action in self.action.forward(prior_reward):
            print(action)

            predicted_step = await self.world_model.forward(action)
            predicted_loss = await self.cost.forward(predicted_step)

            foresight = (action, predicted_loss.value)
            future_actions.append(foresight)

        action = sorted(future_actions, key=itemgetter(1))[0][0]
        if action_lookahead == 1:
            return action

        final_action = await self.forward(predicted_step, action_lookahead - 1)
        predictions = message_path(step, final_action)
        next_action = next(p for p in predictions if isinstance(p, Action))
        return next_action

    async def backward(self, step: Percept):
        loss = await self.cost.backward(step)
        reward = await self.reward.backward(loss)
        await self.action.backward(reward)
        await self.world_model.backward(reward)
