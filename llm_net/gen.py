from typing import Any, Iterable, List, Optional, Union

from networkx import DiGraph
from networkx.algorithms.dag import is_directed_acyclic_graph
from pyee import EventEmitter
from sorcery import delegate_to_attr

from llm_net.abstract import AbstractObject, Field
from llm_net.message import Message
from llm_net.types import Role


class GenAgent(AbstractObject):
    role: Role = Field(description="used to set the role for messages from this node")
    description: Optional[str] = Field(default=None)
    net: Optional["GenAgentNet"] = Field(default=None, exclude=True)
    event_emitter: EventEmitter = Field(default_factory=EventEmitter, exclude=False)
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
        if not self.description and self.__doc__:
            self.description = self.__doc__

    def allowed_method(self, message) -> bool:
        return True

    def new_message(self, content: str, method: str, **kwargs) -> Message:
        """Helper method for creating a message with the node's role and id."""
        return Message(
            sender=self, role=self.role, method=method, content=content, **kwargs
        )

    def receive(self, message: Message) -> Iterable[Message]:
        if message.sender == self or message.receiver != self:
            return

        self.emit("receive", message)

        method = getattr(self, message.type) if message.type else self.call
        if generator := method(message):
            yield from generator


class SystemAgent(GenAgent):
    """Helper class for nodes whose messages should be set to role = system."""

    role = "system"


class AssistantAgent(GenAgent):
    """Helper class for nodes whose messages should be set to role = assistant."""

    role = "assistant"


class UserAgent(GenAgent):
    """Helper class for nodes whose messages should be set to role = user."""

    role = "user"


class GenAgentNet(SystemAgent):
    graph: DiGraph = Field(default_factory=DiGraph, exclude=True)
    directory: dict[str, GenAgent] = Field(default_factory=dict)
    (nodes, edges, predecessors, successors) = delegate_to_attr("graph")

    @classmethod
    def from_agents(cls, agents: List[Any], **kwargs):
        kwargs["graph"] = DiGraph([cls, *agents])
        return cls(**kwargs)

    @classmethod
    def from_graph(cls, graph: DiGraph, **kwargs):
        agents = list(graph)
        instance = cls(**kwargs, graph=graph)
        instance.graph.add_edges_from([(instance, agents)])
        return instance

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert is_directed_acyclic_graph(self.graph)

    def __getitem__(self, key: str) -> GenAgent:
        return self.directory[key]

    def __contains__(self, key: Union[GenAgent, str]) -> bool:
        match key:
            case GenAgent():
                return key.id in self.directory
            case str():
                return key in self.directory

    def connect(
        self,
        u_of_edge: Union["GenAgentNet", GenAgent],
        v_of_edge: Optional[GenAgent] = None,
        **attr,
    ):
        if isinstance(u_of_edge, GenAgentNet):
            self.graph.add_edges_from(u_of_edge.graph.edges)
            for node in u_of_edge.graph.nodes:
                self.directory[node.id] = node
        elif v_of_edge is None:
            self.graph.add_edge(self, u_of_edge, **attr)
            self.directory[u_of_edge.id] = u_of_edge
            u_of_edge.net = self
        else:
            self.graph.add_edge(u_of_edge, v_of_edge, **attr)
            self.directory[u_of_edge.id] = u_of_edge
            u_of_edge.net = self
            self.directory[v_of_edge.id] = v_of_edge
            v_of_edge.net = self

    def disconnect(
        self, u_of_edge: Union["GenAgentNet", Any], v_of_edge: Optional[Any] = None
    ):
        if isinstance(u_of_edge, GenAgentNet):
            self.graph.remove_edges_from(u_of_edge.graph.edges)
            for node in u_of_edge.graph.nodes:
                del self.directory[node.id]
        elif v_of_edge is None:
            self.graph.remove_edge(self, u_of_edge)
            if u_of_edge not in self.graph.nodes:
                del self.directory[u_of_edge.id]
                del u_of_edge.net
        else:
            self.graph.remove_edge(u_of_edge, v_of_edge)
            if u_of_edge not in self.graph.nodes:
                del self.directory[u_of_edge.id]
                del u_of_edge.net
            if v_of_edge not in self.graph.nodes:
                del self.directory[v_of_edge.id]
                del v_of_edge.net

    def receive(self, message: Message) -> Iterable[Message]:
        assert message.receiver in self.graph
        for response in message.receiver.receive(message):
            if (yield response) == StopIteration:
                break
            yield from self.receive(response)


GenAgent.update_forward_refs()
