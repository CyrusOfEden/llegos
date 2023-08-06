"""
https://drive.google.com/file/d/1wzHohvoSgKGZvzOWqZybjm4M4veKR6t3/view
"""

from llegos.ephemeral import EphemeralActor, EphemeralMessage
from llegos.networks import ActorNetwork


class Percept(EphemeralMessage):
    ...


class Configurator(EphemeralActor):
    "Configures other modules for the task at hand"


class Perception(EphemeralActor):
    "Infers the state of the world"

    def percept(self, o: Percept):
        ...


class WorldModel(EphemeralActor):
    ...


class Actor(EphemeralActor):
    ...


class Cost(EphemeralActor):
    ...


class LeCun(ActorNetwork):
    ...
