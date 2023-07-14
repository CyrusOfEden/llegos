from typing import Iterable, List, Literal, Union

from pydantic import Field

from llambdao.base import Node
from llambdao.message import Message, MessageType

HarmoniMessageType: Union[str, MessageType, Literal["accept-proposal"]]


class HarmoniMessage(Message):
    type: HarmoniMessageType


class SelfBeliefsNode(Node):
    role = "user"
    items: List[str] = Field(default_factory=list)

    def revise(self, message: Message) -> Iterable[Message]:
        pass


class MinecraftAgentNode(Node):
    def __init__(self, **fields):
        super().__init__(**fields)
        self.mineplayer.on("chat", self.chat)


class AgentNode(Node):
    minecraft: MinecraftAgentNode
    my_beliefs: SelfBeliefsNode
    world_model: WorldModelNode
    my_desires: SelfDesiresNode

    def step(self, message):
        """Have the agent process the world"""
        pass

    def inform(self, message):
        pass

    def chat(self, message):
        pass

    def request(self, message):
        """Ask this agent to do something."""
        pass
        """Ask this agent to do something."""
        pass
