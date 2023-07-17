from typing import Any, Iterable, Optional, Union

from networkx import DiGraph, is_directed_acyclic_graph
from sorcery import delegate_to_attr

from llm_net.gen import Field, GenAgent, SystemAgent
from llm_net.message import Message


class GenNetwork(SystemAgent):
    graph: DiGraph = Field(default_factory=DiGraph, exclude=True)
    directory: dict[str, GenAgent] = Field(default_factory=dict)
    (nodes, edges, predecessors, successors) = delegate_to_attr("graph")

    @classmethod
    def from_agents(cls, agents: list[Any], **kwargs):
        instance = cls(**kwargs)
        instance.graph.add_edges_from([(instance, agents)])
        return instance

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
        u_of_edge: Union["GenNetwork", GenAgent],
        v_of_edge: Optional[GenAgent] = None,
        **attr,
    ):
        if isinstance(u_of_edge, GenNetwork):
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
        self, u_of_edge: Union["GenNetwork", Any], v_of_edge: Optional[Any] = None
    ):
        if isinstance(u_of_edge, GenNetwork):
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

    def broadcast(self, message: Message) -> Iterable[Message]:
        for node in self.graph.nodes:
            if node is not message.sender:
                for response in node.receive(message):
                    yield response
                    yield from self.receive(response)


GenAgent.update_forward_refs()
GenAgent.update_forward_refs()
