from typing import Any, Callable, Iterable, Optional, Union

from networkx import DiGraph, is_directed_acyclic_graph
from sorcery import delegate_to_attr

from llm_net.gen import Field, GenAgent, SystemAgent
from llm_net.message import Message


class GenNetwork(SystemAgent):
    directory: dict[str, GenAgent] = Field(default_factory=dict)
    graph: DiGraph = Field(default_factory=DiGraph, exclude=True)
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
        v_of_edge: Optional[Callable] = None,
        **attr,
    ):
        if isinstance(u_of_edge, GenNetwork):
            self.graph.add_edges_from(u_of_edge.graph.edges)
            for node in u_of_edge.graph.nodes:
                self.directory[node.id] = node
        elif v_of_edge is None:
            self.graph.add_edge(self, u_of_edge, **attr)
            self.directory[u_of_edge.id] = u_of_edge
        else:
            self.graph.add_edge(u_of_edge, v_of_edge, **attr)
            self.directory[u_of_edge.id] = u_of_edge
            self.directory[v_of_edge.id] = v_of_edge

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
        else:
            self.graph.remove_edge(u_of_edge, v_of_edge)
            if u_of_edge not in self.graph.nodes:
                del self.directory[u_of_edge.id]
            if v_of_edge not in self.graph.nodes:
                del self.directory[v_of_edge.id]

    def propogate(self, message: Message) -> Iterable[Message]:
        agent: GenAgent = message.receiver
        assert agent in self.graph

        for response in agent.receive(message):
            if (yield response) == StopIteration:
                break
            yield from self.receive(response)


GenNetwork.update_forward_refs()


def gen_1():
    response = yield 42
    if response < 100:
        yield 128


def gen_2():
    response = yield 128
    if response < 100:
        yield 256


def test_channel():
    a, b = gen_1(), gen_2()

    a_res = a.send(64)
    assert a_res == 42

    b_res = b.send(a_res)
    assert b_res == 128

    assert next(a) == 128
    assert next(b) == 256


def test_network():
    agents = [GenAgent() for _ in range(10)]
    graph = DiGraph()

    # Create a graph of agents
    for agent_u in agents:
        for agent_v in agents:
            if agent_u != agent_v:
                graph.add_edge(agent_u, agent_v)
                agent_u.on("chat", agent_v.chat)

    graph.remove_edge(agents[2], agents[4])
    agents[2].remove_listener("chat", agents[4].chat)
