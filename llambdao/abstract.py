from abc import ABC
from typing import Any, Dict
from uuid import uuid4

from pydantic import BaseModel, Field

from llambdao.types import Metadata, Role


class AbstractObject(ABC, BaseModel):
    class Config:
        arbitrary_types_allowed = True

    id: str = Field(default="", title="unique identifier")
    metadata: Metadata = Field(default_factory=dict)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = self.id or self.__class__.__name__ + ":" + str(uuid4())


class AbstractNode(AbstractObject, ABC):
    """Nodes can be composed into graphs."""

    class Edge(AbstractObject):
        """Edges point to other nodes."""

        node: "AbstractNode" = Field()

    role: Role = Field()
    edges: Dict[Any, Edge] = Field(default_factory=dict)

    def link(self, to_node: "AbstractNode", **metadata):
        self.edges[to_node.id] = self.Edge(node=to_node, metadata=metadata)

    def unlink(self, from_node: "AbstractNode"):
        del self.edges[from_node.id]
