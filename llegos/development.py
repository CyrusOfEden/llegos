from collections.abc import AsyncIterable, Awaitable, Iterable
from datetime import datetime
from uuid import uuid4

from beartype.typing import Callable
from pyee.asyncio import AsyncIOEventEmitter
from sorcery import delegate_to_attr
from sqlalchemy import text
from sqlmodel import Field, Relationship, SQLModel

from llegos import research


class Object(SQLModel, research.Object):
    id: uuid4 = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        include=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()"), "unique": True},
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        include=True,
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        include=True,
        sa_column_kwargs={"server_default": text("now()"), "onupdate": text("now()")},
    )


class State(Object):
    __tablename__ = "states"

    actor_id: uuid4 = Field(nullable=False, index=True)


class Actor(Object, research.Actor, table=True):
    __tablename__ = "actors"

    state: State = Relationship(
        foreign_key="actor_states.actor_id",
        back_populates="agent",
        sa_relationship_args={"lazy": "join"},
    )
    messages_sent: list["Message"] = Relationship(
        foreign_key="messages.sender_id",
        back_populates="sender",
        sa_relationship_args={"lazy": "select"},
    )
    messages_received: list["Message"] = Relationship(
        foreign_key="messages.receiver_id",
        back_populates="receiver",
        sa_relationship_args={"lazy": "select"},
    )

    event_emitter: AsyncIOEventEmitter = Field(
        default_factory=AsyncIOEventEmitter,
        description="emitting events is non-blocking",
        exclude=True,
    )

    async def instruct(self, message: "Message") -> AsyncIterable["Message"]:
        self.emit("receive", message)

        response = getattr(self, f"on_{message.intent}")(message)

        match response:
            case Awaitable():
                reply = await response
                if reply:
                    yield reply
            case Message():
                yield response
            case AsyncIterable():
                async for reply in response:
                    yield reply
            case Iterable():
                for reply in response:
                    yield reply


class Message(Object, research.Message, table=True):
    __tablename__ = "messages"

    intent: str = Field(index=True, nullable=False, include=True)
    sender_id: uuid4 | None = Field(
        default=None, index=True, nullable=True, include=True
    )
    receiver_id: uuid4 | None = Field(
        default=None, index=True, nullable=True, include=True
    )
    parent_id: uuid4 | None = Field(
        default=None, index=True, nullable=True, foreign_key="messages.id", include=True
    )
    role = delegate_to_attr("sender")

    # Relationships
    sender: Actor | None = Relationship(
        back_populates="messages", sa_relationship_args={"lazy", "select"}
    )
    receiver: Actor | None = Relationship(
        back_populates="messages", sa_relationship_args={"lazy", "select"}
    )
    parent: "Message" | None = Relationship(
        back_populates="children",
        sa_relationship_args={"lazy": "select"},
        sa_relationship_kwargs={"remote_side": "Message.id"},
    )
    children: list["Message"] = Relationship(
        back_populates="parent", sa_relationship_args={"lazy": "select"}
    )


Message.update_forward_refs()
Actor.update_forward_refs()


async def send(message: Message) -> AsyncIterable[Message]:
    if actor := message.receiver:
        async for response in actor.instruct(message):
            yield response


async def send_and_propogate(
    message: Message, applicator: Callable[[Message], AsyncIterable[Message]] = send
) -> AsyncIterable[Message]:
    async for base_res in applicator(message):
        yield base_res
        async for recur_res in send_and_propogate(base_res, applicator=applicator):
            yield recur_res
