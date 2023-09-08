from itertools import permutations

from llegos.research import Actor, Field, Scene


class Pairwise(Scene):
    agents: set[Actor] = Field(min_items=2)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for a1, a2 in permutations(self.agents, 2):
            self.relationships.add_edge(a1, a2)
