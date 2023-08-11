from datetime import datetime
from uuid import uuid4

from beartype.typing import Optional
from pydantic import UUID4
from sorcery import delegate_to_attr
from sqlalchemy import text
from sqlmodel import Field, Relationship, SQLModel

from llegos.ephemeral import (
    EphemeralBehavior,
    EphemeralAgent,
    EphemeralMessage,
    EphemeralObject,
)


class AbstractDurableObject(SQLModel, EphemeralObject):
    id: UUID4 = Field(
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


class DurableMessage(AbstractDurableObject, EphemeralMessage, table=True):
    __tablename__ = "messages"

    intent: str = Field(index=True, nullable=False, include=True)
    sender_id: Optional[uuid4] = Field(
        default=None, index=True, nullable=True, include=True
    )
    receiver_id: Optional[uuid4] = Field(
        default=None, index=True, nullable=True, include=True
    )
    parent_id: Optional[uuid4] = Field(
        default=None, index=True, nullable=True, foreign_key="messages.id", include=True
    )
    role = delegate_to_attr("sender")

    # Relationships
    sender: Optional["DurableAgent"] = Relationship(
        back_populates="messages", sa_relationship_args={"lazy", "select"}
    )
    receiver: Optional["DurableAgent"] = Relationship(
        back_populates="messages", sa_relationship_args={"lazy", "select"}
    )
    parent: Optional["DurableMessage"] = Relationship(
        back_populates="children",
        sa_relationship_args={"lazy": "select"},
        sa_relationship_kwargs={"remote_side": "Message.id"},
    )
    children: list["DurableMessage"] = Relationship(
        back_populates="parent", sa_relationship_args={"lazy": "select"}
    )


class DurableAgent(AbstractDurableObject, EphemeralAgent):
    __tablename__ = "agents"

    actors: "DurableAgent" = Relationship(
        foreign_key="actors.agent_id",
        back_populates="agent",
        sa_relationship_kwargs={"lazy": "join"},
    )


class DurableBehavior(AbstractDurableObject, EphemeralBehavior):
    __tablename__ = "actors"

    agent_id: UUID4 = Field(nullable=False, index=True)
    agent: DurableAgent = Relationship(
        foreign_key="cognition.agent_id",
        back_populates="agent",
        sa_relationship_args={"lazy": "join"},
    )
    messages_sent: list[DurableMessage] = Relationship(
        foreign_key="messages.sender_id",
        back_populates="sender",
        sa_relationship_args={"lazy": "select"},
    )
    messages_received: list[DurableMessage] = Relationship(
        foreign_key="messages.receiver_id",
        back_populates="receiver",
        sa_relationship_args={"lazy": "select"},
    )


DurableAgent.update_forward_refs()
DurableMessage.update_forward_refs()
