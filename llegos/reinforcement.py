from abc import ABC, abstractmethod
from operator import itemgetter
from typing import AsyncIterable

from networkx import DiGraph
from pydantic import Field

from llegos.asyncio import AsyncAgent
from llegos.messages import Action, Inform, Step, message_path, nearest_parent


class Loss(Inform):
    value: float = Field(gte=0)


class LossAgent(AsyncAgent, ABC):
    loss_landscape: DiGraph = Field(
        default_factory=DiGraph, include=False, exclude=True
    )

    @abstractmethod
    async def forward(self, predicted_step: Step) -> Loss:
        action: Action = predicted_step.parent
        previous_step: Step = action.parent
        loss = Loss.reply_to(action, value=0)

        self.loss_landscape.add_edge(previous_step, predicted_step, weight=loss.value)

        return loss

    @abstractmethod
    async def backward(self, realized_step: Step) -> Loss:
        action: Action = realized_step.parent

        edge = self.loss_landscape[action][realized_step]
        predicted_loss = edge["weight"]
        actual_loss = 0

        edge["weight"] = actual_loss
        edge["error"] = predicted_loss - actual_loss

        return Loss.reply_to(realized_step, value=actual_loss)


class Reward(Inform):
    value: float = Field(default=0)


class RewardAgent(AsyncAgent, ABC):
    reward_path: DiGraph = Field(default_factory=DiGraph, include=False, exclude=True)

    @abstractmethod
    async def forward(self, message: Loss) -> Reward:
        reward = Reward.reply_to(message, value=0)

        gen = message.parent
        re = gen.parent
        self.reward_path.add_weighted_edges_from([(re, gen, reward.value)])

        return reward

    @abstractmethod
    async def backward(self, message: Loss) -> Reward:
        reward = Reward.reply_to(message, value=1)

        gen = message.parent
        re = gen.parent
        self.reward_path.add_weighted_edges_from([(re, gen, reward.value)])

        return reward


class ActionAgent(AsyncAgent, ABC):
    @abstractmethod
    async def forward(self, current_step: Step) -> AsyncIterable[Action]:
        "Predict possible actions from a given step."
        yield Action.reply_to(current_step, text="Possible Action #1")
        yield Action.reply_to(current_step, text="Possible Action #2")
        yield Action.reply_to(current_step, text="Possible Action #3")

    @abstractmethod
    async def backward(self, realized_step: Step):
        "Update the model based on the material step."
        ...


class WorldModelAgent(AsyncAgent, ABC):
    @abstractmethod
    async def forward(self, action: Action) -> Step:
        "Predict the next step of the world based on the action."
        predicted_step = Step.reply_to(action)
        return predicted_step

    @abstractmethod
    async def backward(self, realized_step: Step):
        "Update the model based on the material step."
        nearest_parent(realized_step, Action)


class ReinforcementAgent(AsyncAgent, ABC):
    loss: LossAgent = Field(exclude=True)
    rewarder: RewardAgent = Field(exclude=True)
    action: ActionAgent = Field(exclude=True)
    world_model: WorldModelAgent = Field(exclude=True)

    async def forward(self, step: Step, action_horizon: int) -> Action:
        if action_horizon <= 0:
            raise ValueError("search_depth must be greater than 0")

        predicted_actions: list[tuple[Action, float]] = []

        prior_loss = await self.loss.forward(step)
        prior_reward = await self.rewarder.forward(prior_loss)

        async for action in self.action.forward(prior_reward):
            print(action)

            predicted_step = await self.world_model.forward(action)
            predicted_loss = await self.loss.forward(predicted_step)

            predicted_actions.append((action, predicted_loss.value))

        action = sorted(predicted_actions, key=itemgetter(1))[0][0]
        if action_horizon == 1:
            return action

        final_action = await self.forward(predicted_step, action_horizon - 1)
        predictions = message_path(step, final_action)
        next_action = next(p for p in predictions if isinstance(p, Action))
        return next_action

    async def backward(self, step: Step):
        loss = await self.loss.backward(step)
        reward = await self.rewarder.backward(loss)
        await self.action.backward(reward)
        await self.world_model.backward(reward)
