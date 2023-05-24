from abc import ABCMeta
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AbstractObject(BaseModel, meta=ABCMeta):
    class Config:
        allow_arbitrary_types = True


Metadata = Dict[str, Any]


class Message(AbstractObject):
    body: str = Field()
    sender: Optional[str] = Field()
    recipient: Optional[str] = Field()
    thread: Optional[str] = Field(default=None)
    metadata: Optional[Metadata] = Field(default=None)

    @classmethod
    def inform(cls, *args, **kwargs):
        metadata = {**kwargs.pop("metadata", {}), "action": "inform"}
        return cls(
            *args,
            **kwargs,
            metadata=metadata
        )

    @classmethod
    def request(cls, *args, **kwargs):
        metadata = {**kwargs.pop("metadata", {}), "action": "request"}
        return cls(
            *args,
            **kwargs,
            metadata=metadata
        )

    @classmethod
    def new_reply(
        cls, to_message: "Message", with_body: str, and_metadata: Metadata = {}
    ):
        metadata = {**to_message.metadata, **and_metadata}
        return cls(
            to=to_message.sender,
            sender=to_message.recipient,
            body=with_body,
            thread=to_message.thread,
            metadata=metadata,
        )

    @property
    def action(self) -> str:
        return self.metadata["action"]


class AbstractAgent(AbstractObject, meta=ABCMeta):  # noqa: F821
    def inform(self, message: Message) -> None:
        raise NotImplementedError()

    def request(self, message: Message) -> Message:
        raise NotImplementedError()


class Entry(AbstractObject):
    agent: AbstractAgent = Field()
    metadata: Optional[Metadata] = Field(default=None)


class AgentDispatcher(AbstractObject, meta=ABCMeta):
    lookup: Dict[str, Entry] = Field(default_factory=dict)

    def register(self, agent: AbstractAgent, name: str, **metadata):
        self.lookup[name] = Entry(agent, metadata)

    def deregister(self, name: str):
        del self.lookup[name]

    def route(self, message: Message) -> AbstractAgent:
        return self.lookup[message.recipient].agent

    def dispatch(self, message: Message):
        method = getattr(self.route(message), message.action)
        return method(message)
