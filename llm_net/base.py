from contextvars import ContextVar
from typing import Iterable, Union

from janus import Queue
from networkx import MultiDiGraph, is_directed_acyclic_graph
from pyee import EventEmitter
from sorcery import delegate_to_attr, dict_of

from llm_net.abstract import AbstractObject, Field
from llm_net.message import Message
from llm_net.types import Method, Role


class GenAgent(AbstractObject):
    role: Role = Field(
        default="user", description="used to set the role for messages from this node"
    )
    description: str = Field(default="")
    event_emitter: EventEmitter = Field(default_factory=EventEmitter, exclude=True)
    (
        add_listener,
        emit,
        event_names,
        listeners,
        listens_to,
        on,
        once,
        remove_all_listeners,
        remove_listener,
    ) = delegate_to_attr("event_emitter")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.description and self.__class__.__doc__:
            self.description = self.__class__.__doc__

    @staticmethod
    def network() -> "GenNetwork":
        return llm_net.get()

    def draft_message(self, content: str, method: str, **kwargs) -> Message:
        """Helper method for creating a message with the node's role and id."""
        return Message(
            sender=self, role=self.role, method=method, content=content, **kwargs
        )

    receivable_messages: set[type[Message]] = Field(
        default_factory=set,
        description="set of methodsthat this node can receive",
    )

    @property
    def receivable_methods(self):
        return {message.method for message in self.receivable_messages}

    def can_receive(self, message: Message) -> bool:
        return (
            message.sender != self
            and message.receiver == self
            and message.method in self.receivable_methods
        )

    def receive(self, message: Message) -> Iterable[Message]:
        if not self.can_receive(message):
            raise ValueError(f"Unexpected message {message}")

        self.emit("receive", message)

        method = getattr(self, message.method)
        return method(message)

    @classmethod
    def init_fn(cls):
        schema = cls.schema()

        name = cls.__name__
        description = cls.__doc__
        parameters = schema["properties"]
        required = schema["required"]

        return dict_of(name, description, parameters, required)

    @property
    def receive_fn(self):
        return {
            "name": self.id,
            "description": self.description,
            "parameters": {
                "title": "message",
                "type": "object",
                "oneOf": [
                    message_class.schema() for message_class in self.receivable_messages
                ],
            },
            "required": ["message"],
        }


class AssistantAgent(GenAgent):
    """Helper class for nodes whose messages should be set to role = assistant."""

    role = "assistant"


class SystemAgent(GenAgent):
    """Helper class for nodes whose messages should be set to role = system."""

    role = "system"


class GenChannel(SystemAgent):
    """For something more CSP-lke, use a GenChannel instead of a GenNetwork."""

    _queue: Queue[Message] = Field(default_factory=Queue, exclude=True)

    @property
    def queue(self):
        return self._queue.sync_q

    @property
    def unfinished_tasks(self):
        return self._queue.unfinished_tasks

    (
        maxsize,
        closed,
        task_done,
        qsize,
        empty,
        full,
        put_nowait,
        get_nowait,
        put,
        get,
        join,
    ) = delegate_to_attr("queue")


class GenNetwork(SystemAgent):
    graph: MultiDiGraph = Field(
        default_factory=MultiDiGraph, include=False, exclude=True
    )
    (nodes, edges, predecessors, successors, neighbors) = delegate_to_attr("graph")

    def __init__(self, links: dict[GenAgent, list[tuple[str, GenAgent]]], **kwargs):
        super().__init__(**kwargs)
        for u, edges in links.items():
            for event, v in edges:
                self.link(u, event, v)
        assert is_directed_acyclic_graph(self.graph)

    @property
    def directory(self):
        return {a.id: a for a in self.graph.nodes}

    def __getitem__(self, key: str) -> GenAgent:
        return self.directory[key]

    def __contains__(self, key: Union[str, GenAgent]) -> bool:
        match key:
            case str():
                return key in self.directory
            case GenAgent():
                return key in self.graph.nodes
            case _:
                raise TypeError(f"lookup key must be str or GenAgent, not {type(key)}")

    def link(self, u: GenAgent, event: str, v: GenAgent, **attr):
        if (u, v.receive, event) not in self.graph.edges(keys=True):
            u.add_listener(event, v.receive)
            self.graph.add_edge(u, v.receive, event=event, **attr)

    def unlink(self, u: GenAgent, event: str, v: GenAgent):
        if (u, v.receive, event) in self.graph.edges(keys=True):
            self.graph.remove_edge(u, v.receive, key=event)
            u.remove_listener(event, v.receive)

    def can_receive(self, message: Message) -> bool:
        return (
            message.receiver in self
            and message.sender != message.receiver
            and message.method in self.receivable_methods
            and message.receiver.can_receive(message)
        )

    def receive(self, message: Message) -> Iterable[Message]:
        if not self.can_receive(message):
            raise ValueError(f"Unexpected message {message}")

        self.emit("receive", message)

        previous_net = llm_net.set(self)
        try:
            agent: GenAgent = message.receiver
            for response in agent.receive(message):
                if (yield response) == StopIteration:
                    break
                yield from self.receive(response)
        finally:
            llm_net.reset(previous_net)


class ChatMessage(Message):
    method: Method = "chat"


llm_net = ContextVar[GenNetwork]("llm_net.active_network")
