import functools
import typing as t
from collections.abc import Iterable
from contextvars import ContextVar, Token
from datetime import datetime
from time import time

from beartype import beartype
from beartype.typing import Callable, Iterator, Optional
from deepmerge import always_merger
from ksuid import Ksuid
from networkx import DiGraph, MultiGraph
from pydantic import BaseModel, ConfigDict, Field
from pydash import snake_case
from pyee import EventEmitter
from sorcery import delegate_to_attr, maybe

if t.TYPE_CHECKING:
    from pydantic.main import IncEx

from .logger import getLogger

logger = getLogger("research")


def namespaced_ksuid(prefix: str):
    return f"{prefix}_{Ksuid()}"


def namespaced_ksuid_generator(prefix: str):
    return lambda: namespaced_ksuid(prefix)


class Object(BaseModel):
    """A Pydantic base class for Llegos entities.

    - **Definition:** Objects are the fundamental entities in Llegos, defined using Pydantic models.
        They represent the base class from which other more specialized entities like Messages and
        Actors derive.
    - **Customization:** Users can extend the Object class to create their own network objects,
        complete with validation and serialization capabilities.
    - **Dynamic Generation:** Users can dynamically generate objects using OpenAI function calling,
        [Instructor](https://github.com/jxnl/instructor),
        [Outlines](https://github.com/outlines-dev/outlines), etc.

    Attributes:
        id (str): A unique identifier for the object, generated using namespaced KSUID.
        metadata (dict): A dictionary to store additional metadata about the object.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.model_fields["id"].default_factory = namespaced_ksuid_generator(
            snake_case(cls.__name__)
        )

    id: str = Field(default_factory=namespaced_ksuid_generator("object"))
    metadata: dict = Field(default_factory=dict)

    def model_dump_json(
        self,
        *,
        indent: int | None = None,
        include: "IncEx" = None,
        exclude: "IncEx" = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = True,  # updated default to True to reduce JSON noise sent to the LLM
        round_trip: bool = False,
        warnings: bool = True,
    ) -> str:
        return super().model_dump_json(
            indent=indent,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
        )

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return self.model_dump_json()

    @classmethod
    def lift(cls, instance: "Object", **kwargs):
        """Creates a new instance of the class using an existing object and additional attributes.

        This class method allows for creating a new object based on an existing one, optionally
        overriding or adding new attributes. It's particularly useful for creating derived objects
        with some shared properties.

        Args:
            instance (Object): The existing object to base the new instance on.
            **kwargs: Additional attributes to set on the new object.

        Returns:
            Object: A new instance of the class.
        """
        attrs = instance.model_dump(exclude={"id"})
        always_merger.merge(attrs, kwargs)
        return cls(**attrs)


class MissingNetwork(ValueError):
    ...


class InvalidMessage(ValueError):
    ...


class Actor(Object):
    """Represents an actor in a network, capable of receiving and processing messages.

    This class extends the functionality of the Object class, incorporating message handling
    capabilities in a networked environment. Actors can receive messages, determine appropriate
    handling methods, and emit events. They are also aware of their network and relationships
    within that network.

    - **Roles:** Actors are specialized objects that encapsulate autonomous agents within the
        system. Each actor has its unique behavior, state, and communication abilities.
    - **Interactions:** Actors interact with each other and the environment primarily through
        strongly-typed messages, responding to received information and making decisions based on
        their internal logic and objectives.

    Design Goals:
    1. Actors are a container for your agents that isolate state.
    2. Actors have a mailbox and process messages one by one (to prevent race conditions).
    3. Actors can load state on startup, persist state, and preserve state on shutdown.
    4. Actors can run periodic tasks.
    5. Actors can be composed into static and dynamic graphs.

    Attributes:
        _event_emitter (EventEmitter): An event emitter for handling events.

    Methods:
        can_receive: Checks if the actor can receive a specific type of message.
        receive_missing: Default handler for unrecognized messages.
        receive: Processes a received message and yields responses.
        network: Retrieves the network to which the actor belongs.
        relationships: Provides information about the actor's relationships in the network.
        receivers: Finds actors capable of receiving specified message types.
        add_listener, emit, event_names, listeners, on, once, remove_all_listeners, and
        remove_listener:
            Delegated methods for event handling, proxied to the internal EventEmitter.
    """

    _event_emitter = EventEmitter()

    def can_receive(self, message: t.Union["Message", type["Message"]]) -> bool:
        """
        Determines if the actor can receive a given message or message type.

        Args:
            message (Union[Message, type[Message]]): The message instance or type to be checked.

        Returns:
            bool: True if the actor has a method to receive the message, False otherwise.
        """
        return hasattr(self, self.receive_method_name(message))

    @staticmethod
    def receive_method_name(message: t.Union["Message", type["Message"]]):
        if isinstance(message, Message) and hasattr(message, "intent"):
            return f"receive_{message.intent}"

        intent = snake_case(
            (message.__class__ if isinstance(message, Message) else message).__name__
        )
        return f"receive_{intent}"

    def receive_method(self, message: "Message"):
        method = self.receive_method_name(message)
        if hasattr(self, method):
            return getattr(self, method)
        return self.receive_missing

    def receive_missing(self, message: "Message"):
        raise InvalidMessage(message)

    def __call__(self, message: "Message") -> Iterator["Message"]:
        return self.receive(message)

    def receive(self, message: "Message") -> Iterator["Message"]:
        """Processes a received message and yields response messages.

        This method logs the receipt, emits a 'before:receive' event, and delegates to the
        appropriate handling method based on the message type. The response can be a single message
        or an iterable of messages.

        Args:
            message (Message): The message to be processed.

        Yields:
            Iterator[Message]: An iterator over response messages.
        """
        logger.debug(f"{self.id} before:receive {message.id}")
        self.emit("before:receive", message)

        response = self.receive_method(message)(message)

        match response:
            case Message():
                yield response
            case Iterable():
                yield from response

    @property
    def network(self):
        """Retrieves the network to which this actor belongs.

        Returns:
            Network: The network instance.

        Raises:
            MissingNetwork: If the actor is not part of any network.
        """
        if network := network_context.get():
            return network
        raise MissingNetwork(self)

    @property
    def relationships(self) -> t.Sequence[t.Tuple["Actor", str | None, dict]]:
        """Provides information about this actor's relationships within the network.

        Returns:
            Sequence[Tuple[Actor, str | None, dict]]: A sorted list of tuples containing
                information about each relationship. Each tuple consists of the neighbor
                (Actor), relationship type (str or None), and relationship data (dict).
        """
        return sorted(
            [
                (neighbor, key, data)
                for (_self, neighbor, key, data) in self.network._graph.edges(
                    self,
                    keys=True,
                    data=True,
                )
            ],
            key=lambda edge: edge[2].get("weight", 1),
        )

    def receivers(self, *messages: type["Message"]):
        """Finds actors in the network capable of receiving specified message types.

        Args:
            *messages (type[Message]): Variable number of message types to check for.

        Returns:
            List[Actor]: A list of actors capable of receiving all provided message types.
        """
        return [
            actor
            for (actor, _key, _data) in self.relationships
            if all(actor.can_receive(m) for m in messages)
        ]

    (
        add_listener,
        emit,
        event_names,
        listeners,
        on,
        once,
        remove_all_listeners,
        remove_listener,
    ) = delegate_to_attr("_event_emitter")


class Network(Actor):
    """Represents a network of actors, extending the capabilities of an Actor.

    This class models a network as an actor itself, allowing it to participate in message handling
    and event emission. It maintains a collection of actors and the relationships between them,
    represented as a graph. The Network class provides methods for actor management and interaction
    within the network. The Network can be used as a context manager to limit the scope of Actors'
    relationships.

    - **Dynamic Actor Graphs:** Within networks, you can dynamically manage the actors'
        relationships. Actors operating within the context of the network can access the network
        directory and discover other actors that can receive particular message types.
    - **Infinitely Nestable:** Networks are themselves Actors, allowing for the creation of complex,
        multi-layered environments where different groups of actors can interact within their
        sub-contexts.

    Attributes:
        actors (Sequence[Actor]): A sequence of actors that are part of the network.
        _graph (MultiGraph): An internal representation of the network as a graph.
    """

    actors: t.Sequence[Actor] = Field(default_factory=list)
    _graph = MultiGraph()

    def __init__(self, actors: t.Sequence[Actor], **kwargs):
        super().__init__(actors=actors, **kwargs)
        for actor in actors:
            self._graph.add_edge(self, actor)

    def __getitem__(self, key: str | Actor | t.Any) -> Actor:
        """Retrieves an actor from the network by their ID."""
        match key:
            case str():
                return self.directory[key]
            case _:
                raise TypeError("__getitem__ accepts a key of str", key)

    def __contains__(self, key: str | Actor | t.Any) -> bool:
        """Checks if an actor or actor ID is part of the network."""
        match key:
            case str():
                return key in self.directory
            case Actor():
                return key in self.actors
            case _:
                raise TypeError("__contains__ accepts a key of str or Actor", key)

    @property
    def directory(self):
        """Provides a dictionary mapping actor IDs to actor instances."""
        return {a.id: a for a in self.actors}

    def __enter__(self):
        global network_token, network_context
        network_token = network_context.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global network_token, network_context
        if network_token:
            network_context.reset(network_token)
            network_token = None


# Global State for Network Context Management
network_context = ContextVar[Network]("llegos.network")
network_token: Optional[Token[Network]] = None

"""
The 'network_context' and 'network_token' are used to manage the context of the current network
globally. This is particularly useful for maintaining a reference to the active network instance
across different parts of the application.

- 'network_context': A ContextVar object that holds the current network instance. This variable
  manages the current network scope, through which actors can reliably discover peers that are part
  of that network.

- 'network_token': An optional token that represents the state of the 'network_context' before a
  new  network is set. This token is used to reset the 'network_context' to its previous state,
  ensuring  proper context management, especially in scenarios where networks are dynamically
  created and switched within an application's lifecycle.
"""


class Message(Object):
    """Represents a message in the network, capable of being sent and received by actors.

    - **Purpose:** Messages serve as the primary means of communication between agents. They carry
        information, requests, commands, or any data that needs to be transmitted from one entity
        to another.
    - **Structure and Handling:** Each message has an identifiable structure and is designed to be
        flexible and extensible. The system provides mechanisms for message validation, forwarding,
        replying, and tracking within conversation threads.
    - **Email Semantics:** They are organized into hierarchical trees, allowing for the creation of
        complex communication patterns and protocols. Multiple replies can be sent to a single
        message, and each reply can have its own set of replies, and so on.

    Attributes:
        created_at (datetime): The timestamp of when the message was created.
        sender (Optional[ForwardRef[Actor]]): The sender of the message.
        receiver (Optional[ForwardRef[Actor]]): The intended receiver of the message.
        parent (Optional[ForwardRef[Message]]): The parent message, if this is a reply or forward.

    Methods:
        reply_to: Class method to create a reply to this message.
        forward: Class method to forward this message to another actor.
        sender_id: Property to get the ID of the sender.
        receiver_id: Property to get the ID of the receiver.
        parent_id: Property to get the ID of the parent message.
        forward_to: Instance method to forward this message to another actor.
        reply: Instance method to create a reply to this message.
    """

    created_at: datetime = Field(default_factory=datetime.utcnow, frozen=True)
    sender: Optional[t.ForwardRef("Actor")] = None
    receiver: Optional[t.ForwardRef("Actor")] = None
    parent: Optional[t.ForwardRef("Message")] = None

    @classmethod
    def reply_to(cls, message: "Message", **kwargs) -> "Message":
        """Creates a reply to a given message.

        This class method constructs a new message that acts as a reply to the given message.
        The new message's sender is set to the original receiver, and its receiver is set to
        the original sender.

        Args:
            message (Message): The message to which a reply is being made.
            **kwargs: Additional attributes to be set on the new message.

        Returns:
            Message: The newly created reply message.
        """
        attrs = {
            "sender": message.receiver,
            "receiver": message.sender,
            "parent": message,
        }
        attrs.update(kwargs)
        return cls.lift(message, **attrs)

    @classmethod
    def forward(cls, message: "Message", receiver: Actor, **kwargs) -> "Message":
        """Forwards a message to a different receiver.

        This method creates a new message that is a forward of the given message. The new message's
        sender is set to the original message's receiver, and its receiver is the specified new
        receiver.

        Args:
            message (Message): The message to be forwarded.
            receiver (Actor): The actor to whom the message will be forwarded.
            **kwargs: Additional attributes to be set on the new forwarded message.

        Returns:
            Message: The newly created forwarded message.
        """
        attrs = {
            "sender": message.receiver,
            "receiver": receiver,
            "parent": message,
        }
        attrs.update(kwargs)
        return cls.lift(message, **attrs)

    @property
    def sender_id(self) -> Optional[str]:
        """Gets the ID of the sender of the message, if available."""
        return maybe(self.sender).id

    @property
    def receiver_id(self) -> Optional[str]:
        """Gets the ID of the receiver of the message, if available."""
        return maybe(self.receiver).id

    @property
    def parent_id(self) -> Optional[str]:
        """Gets the ID of the parent message, if this message is part of a chain."""
        return maybe(self.parent).id

    def __str__(self):
        return self.model_dump_json(exclude={"parent"})

    def forward_to(self, receiver: Actor, **kwargs) -> "Message":
        """Forward this message to another actor.

        Args:
            receiver (Actor): The actor to whom the message will be forwarded.
            **kwargs: Additional attributes to be set on the new forwarded message.

        Returns:
            Message: The newly created forwarded message.
        """
        return self.forward(self, receiver, **kwargs)

    def reply(self, **kwargs) -> "Message":
        """
        Instance method to create a reply to this message.

        Args:
            **kwargs: Additional attributes to be set on the new reply message.

        Returns:
            Message: The newly created reply message.
        """
        return self.reply_to(self, **kwargs)


@beartype
def message_chain(message: Message | None, height: int) -> Iterator[Message]:
    """Generates an iterator over a chain of messages up to a specified height.

    This function iterates over the ancestors of a given message, up to a specified height,
    creating a chain of messages. It starts from the given message and moves up to its parent
    messages recursively.

    Args:
        message (Message | None): The starting message from which to trace the chain.
        height (int): The maximum number of levels to trace back from the given message.

    Returns:
        Iterator[Message]: An iterator over the message chain.
    """
    if message is None:
        return []
    elif height > 1:
        yield from message_chain(message.parent, height - 1)
    yield message


@beartype
def message_list(message: Message, height: int) -> t.List[Message]:
    """Creates a list of messages in the message chain up to a specified height.

    This function constructs a list containing the chain of messages starting from a given
    message and moving up through its ancestors, limited by the specified height.

    Args:
        message (Message): The starting message for the list.
        height (int): The maximum number of levels to include in the list.

    Returns:
        List[Message]: A list of messages in the chain.
    """
    return list(message_chain(message, height))


@beartype
def message_tree(messages: Iterable[Message]):
    """Constructs a directed graph representing the tree structure of a collection of messages.

    This function builds a directed graph (DiGraph) from an iterable of messages, where edges
    represent the parent-child relationship between messages.

    Args:
        messages (Iterable[Message]): An iterable of messages to construct the tree from.

    Returns:
        DiGraph: A directed graph representing the message tree.
    """

    g = DiGraph()
    for message in messages:
        if message.parent:
            g.add_edge(message.parent, message)
    return g


class MessageNotFound(ValueError):
    ...


def message_ancestors(message: Message) -> Iterator[Message]:
    """Generates an iterator over the ancestors of a given message.

    This function iterates over all the parent messages of a given message, tracing back through
    its lineage.

    Args:
        message (Message): The message from which to start tracing back.

    Returns:
        Iterator[Message]: An iterator over the ancestors of the message.
    """
    while message := message.parent:
        yield message


@beartype
def message_closest(
    message: Message,
    cls_or_tuple: tuple[type[Message]] | type[Message],
    max_search_height: int = 256,
) -> Optional[Message]:
    """Finds the closest ancestor of a given message that matches a specified type.

    This function searches through the message's ancestors up to a maximum height, looking for a
    message that matches the specified type or tuple of types.

    Args:
        message (Message): The starting message for the search.
        cls_or_tuple (tuple[type[Message]] | type[Message]): The message type(s) to search for.
        max_search_height (int, optional): The maximum height to search. Defaults to 256.

    Returns:
        Optional[Message]: The closest matching ancestor, or None if not found.

    Raises:
        MessageNotFound: If no matching message is found within the max_search_height.
    """
    for parent, _ in zip(message_ancestors(message), range(max_search_height)):
        if isinstance(parent, cls_or_tuple):
            return parent
    else:
        raise MessageNotFound(cls_or_tuple)


class MissingReceiver(ValueError):
    ...


@beartype
def message_send(message: Message) -> Iterator[Message]:
    """Sends a message to its intended receiver and yields any response messages.

    This function triggers the receipt and processing of the message by its receiver, assuming the
    receiver is specified. It yields any messages that are produced as a response by the receiver.

    Args:
        message (Message): The message to be sent.

    Returns:
        Iterator[Message]: An iterator over the response messages from the receiver.

    Raises:
        MissingReceiver: If the message does not have a specified receiver.
    """
    if not message.receiver:
        raise MissingReceiver(message)
    yield from message.receiver.receive(message)


@beartype
def message_propagate(
    message: Message,
    send_fn: Callable[[Message], Iterator[Message]] = message_send,
) -> Iterator[Message]:
    """Propagates a message through the network, yielding all response messages.

    This function sends a message (using the provided send function) and recursively propagates
    any response messages. It is useful for handling chains of messages that generate further
    messages as responses.

    Args:
        message (Message): The initial message to be propagated.
        send_fn (Callable[[Message], Iterator[Message]], optional): The function used to send
            messages. Defaults to message_send.

    Returns:
        Iterator[Message]: An iterator over all messages generated in the propagation process.
    """
    for reply in send_fn(message):
        if reply:
            yield reply
            yield from message_propagate(reply, send_fn)


def throttle(seconds):
    """Decorator that limits the execution frequency of a function.

    This decorator ensures that the decorated function can only be called once every specified
    number of seconds. Subsequent calls within the throttle period are ignored.

    Args:
        seconds (float): The minimum number of seconds between successive calls to the function.

    Returns:
        Callable: The throttled function.
    """

    def decorate(f):
        t = None

        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            nonlocal t
            start = time()
            if t is None or start - t >= seconds:
                result = f(*args, **kwargs)
                t = start
                return result

        return wrapped

    return decorate


Object.model_rebuild()
Message.model_rebuild()
Actor.model_rebuild()
Network.model_rebuild()
