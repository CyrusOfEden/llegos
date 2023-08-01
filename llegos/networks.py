from contextvars import ContextVar
from operator import itemgetter
from typing import AsyncIterable

from networkx import MultiGraph
from sorcery import delegate_to_attr

from llegos.asyncio import AsyncAgent, EphemeralMessage, async_propogate
from llegos.ephemeral import Field
from llegos.roles import SystemAgent


class NetworkAgent(AsyncAgent):
    @property
    def network(self):
        return network_context.get()

    @property
    def relationships(self):
        return sorted(self.network.edges(self), key=itemgetter("weight"))


class AgentNetwork(NetworkAgent, SystemAgent):
    graph: MultiGraph = Field(default_factory=MultiGraph, include=False, exclude=True)

    def __contains__(self, key: str | NetworkAgent) -> bool:
        match key:
            case str():
                return key in self.directory
            case NetworkAgent():
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

    async def receive(
        self, message: EphemeralMessage
    ) -> AsyncIterable[EphemeralMessage]:
        self.emit(message.intent, message)

        previous_network = network_context.set(self)
        try:
            return async_propogate(message)
        finally:
            network_context.reset(previous_network)


network_context = ContextVar("llegos.networks.context", default=AgentNetwork())
