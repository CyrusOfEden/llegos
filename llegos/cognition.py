from abc import ABC


class Cognition(ABC):
    @property
    def language(self):
        ...

    @property
    def working_memory(self):
        ...

    @property
    def short_term_memory(self):
        ...

    @property
    def long_term_memory(self):
        ...
