from abc import ABC
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field


class AbstractObject(BaseModel, ABC):
    class Config:
        arbitrary_types_allowed = True

    id: str = Field()
    metadata: dict = Field(default_factory=dict)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = self.__class__.__name__ + ":" + str(uuid4())

    def __str__(self):
        return yaml.dump(self.dict(), sort_keys=False)

    def __hash__(self):
        return hash(self.id)

    @classmethod
    @property
    def init_schema(cls):
        schema = cls.schema()

        parameters = schema["properties"]
        del parameters["id"]

        return {
            "name": cls.__name__,
            "description": cls.__doc__,
            "parameters": parameters,
            "required": schema["required"],
        }
