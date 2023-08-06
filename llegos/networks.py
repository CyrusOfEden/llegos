from contextlib import contextmanager
from contextvars import ContextVar

from networkx import MultiGraph
from sorcery import delegate_to_attr

from llegos.asyncio import AsyncActor, async_propogate
from llegos.ephemeral import EphemeralMessage, Field


class Propogate(EphemeralMessage):
    message: EphemeralMessage = Field()


class NetworkActor(AsyncActor):
    @property
    def network(self):
        return network_context.get()

    @property
    def relationships(self):
        edges = [
            (neighbor, key, data)
            for (node, neighbor, key, data) in self.network.edges(keys=True, data=True)
            if node == self
        ]
        edges.sort(key=lambda edge: edge[2].get("weight", 1))
        return [agent for (agent, _, _) in edges]

    def receivers(self, *messages: type[EphemeralMessage]):
        return [
            agent
            for agent in self.relationships
            if any(m in agent.receivable_messages for m in messages)
        ]


class ActorNetwork(NetworkActor):
    graph: MultiGraph = Field(default_factory=MultiGraph, include=False, exclude=True)

    def __contains__(self, key: str | NetworkActor) -> bool:
        match key:
            case str():
                return key in self.directory
            case NetworkActor():
                return key in self.graph
            case _:
                raise TypeError(
                    f"lookup key must be str or AsyncGenAgent, not {type(key)}"
                )

    (
        __getitem__,
        add_edges_from,
        add_weighted_edges_from,
        edges,
        get_edge_data,
        has_edge,
        neighbors,
        nodes,
        remove_edges_from,
    ) = delegate_to_attr("graph")

    @property
    def directory(self):
        return {a.id: a for a in self.graph.nodes}

    async def propogate(self, p: Propogate):
        with self.context():
            async for message in async_propogate(p.message):
                yield message

    @contextmanager
    def context(self):
        try:
            rollback = network_context.set(self)
            yield self
        finally:
            network_context.reset(rollback)


network_context = ContextVar[ActorNetwork]("llegos.networks.context")
