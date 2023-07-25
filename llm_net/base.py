from contextvars import ContextVar
from typing import Iterable, Optional, Union

from networkx import MultiDiGraph, is_directed_acyclic_graph
from pyee import EventEmitter
from sorcery import delegate_to_attr, dict_of

from llm_net.abstract import AbstractObject, Field
from llm_net.message import Message
from llm_net.types import Role

llm_net = ContextVar("llm_net.active_network")


class GenAgent(AbstractObject):
    role: Role = Field(
        default="user", description="used to set the role for messages from this node"
    )
    description: str = Field(default="")
    event_emitter: EventEmitter = Field(default_factory=EventEmitter, exclude=True)
    (
        add_listener,
        emit,
        event_names,
        listeners,
        listens_to,
        on,
        once,
        remove_all_listeners,
        remove_listener,
    ) = delegate_to_attr("event_emitter")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.description and self.__class__.__doc__:
            self.description = self.__class__.__doc__

    @staticmethod
    def network() -> "GenNetwork":
        return llm_net.get()

    def draft_message(self, content: str, method: str, **kwargs) -> Message:
        """Helper method for creating a message with the node's role and id."""
        return Message(
            sender=self, role=self.role, method=method, content=content, **kwargs
        )

    receivable_messages: set[type[Message]] = Field(
        default_factory=set,
        description="set of message types that this node can receive",
    )

    def receive(self, message: Message) -> Iterable[Message]:
        if message.sender == self or message.receiver != self:
            return None

        self.emit("receive", message)

        method = getattr(self, message.type) if message.type else self.call
        return method(message)

    @classmethod
    def init_fn(cls):
        schema = cls.schema()

        name = cls.__name__
        description = cls.__doc__
        parameters = schema["properties"]
        required = schema["required"]

        return dict_of(name, description, parameters, required)

    @property
    def receive_fn(self):
        return {
            "name": self.id,
            "description": self.description,
            "parameters": {
                "title": "message",
                "type": "object",
                "oneOf": [
                    message_class.schema() for message_class in self.receivable_messages
                ],
            },
            "required": ["message"],
        }


class SystemAgent(GenAgent):
    """Helper class for nodes whose messages should be set to role = system."""

    role = "system"


class AssistantAgent(GenAgent):
    """Helper class for nodes whose messages should be set to role = assistant."""

    role = "assistant"


class GenNetwork(SystemAgent):
    graph: MultiDiGraph = Field(
        default_factory=MultiDiGraph, include=False, exclude=True
    )
    (nodes, edges, predecessors, successors) = delegate_to_attr("graph")

    def __init__(self, agents: list[GenAgent], **kwargs):
        graph = MultiDiGraph()
        for agent in agents:
            for event in agent.event_names():
                for listener in agent.listeners(event):
                    graph.add_edge(agent, listener, key=event)

        super().__init__(**kwargs)
        assert is_directed_acyclic_graph(self.graph)

    @property
    def directory(self):
        return {a.id: a for a in self.graph.nodes}

    def __getitem__(self, key: str) -> GenAgent:
        return self.directory[key]

    def __contains__(self, key: Union[str, GenAgent]) -> bool:
        match key:
            case str():
                return key in self.directory
            case GenAgent():
                return key in self.graph.nodes
            case _:
                raise TypeError(f"lookup key must be str or GenAgent, not {type(key)}")

    def link(self, u: GenAgent, event: str, v: GenAgent, **attr):
        self.graph.add_edge(u, v.receive, event=event, **attr)
        u.add_listener(event, v.receive)

    def unlink(self, u: GenAgent, event: str, v: GenAgent):
        self.graph.remove_edge(u, v.receive, key=event)
        u.remove_listener(event, v.receive)

    def receive(self, message: Message) -> Iterable[Message]:
        agent: Optional[GenAgent] = message.receiver
        if agent is None:
            return
        if agent not in self:
            raise ValueError(f"Receiver {agent.id} not in GenNetwork")

        self.emit("receive", message)

        previous_network = llm_net.set(self)
        try:
            for response in agent.receive(message):
                if (yield response) == StopIteration:
                    break
                yield from self.receive(response)
        finally:
            llm_net.reset(previous_network)
