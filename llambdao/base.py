from pydantic import BaseModel


class BaseObject(BaseModel):
    class Config:
        allow_arbitrary_types = True
