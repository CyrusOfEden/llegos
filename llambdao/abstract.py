from abc import ABC
from uuid import uuid4

from pydantic import BaseModel, Field

from llambdao.types import Metadata


class AbstractObject(ABC, BaseModel):
    class Config:
        arbitrary_types_allowed = True

    id: str = Field(default="", title="unique identifier")
    metadata: Metadata = Field(default_factory=dict)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = self.id or self.__class__.__name__ + ":" + str(uuid4())
