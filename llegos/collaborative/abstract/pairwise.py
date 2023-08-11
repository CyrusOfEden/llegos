from itertools import permutations

from llegos.contexts import Context, ContextualRole, Field


class PairwiseContext(Context):
    agents: set[ContextualRole] = Field(min_items=2)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for a1, a2 in permutations(self.agents, 2):
            self.graph.add_edge(a1, a2)
