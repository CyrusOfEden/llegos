from datetime import datetime
from textwrap import dedent
from typing import Optional
from uuid import uuid4

from pydantic import UUID4
from sorcery import delegate_to_attr
from sqlalchemy import text
from sqlmodel import Field, Relationship, SQLModel

from llegos.ephemeral import EphemeralAgent, EphemeralMessage, EphemeralObject
from llegos.messages import Intent


class AbstractDurableObject(SQLModel, EphemeralObject):
    id: UUID4 = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("gen_random_uuid()"), "unique": True},
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("now()"), "onupdate": text("now()")},
    )

    def __hash__(self):
        return hash(self.id)


class DurableMessage(AbstractDurableObject, EphemeralMessage, table=True):
    __tablename__ = "messages"

    intent: Intent = Field(
        description=dedent(
            """\
            Agents call methods named after the intent of the message.

            A curated set of intents to consider:
            - chat = "chat about this topic", "talk about this topic", etc.
            - request = "request this thing", "ask for this thing", etc.
            - response = "responding with this thing", "replying with this thing", etc.
            - query = "query for information"
            - inform = "inform of new data", "tell about this thing", etc.
            - proxy = "route this message to another agent"
            - step = process the environment, a la multi agent reinforcement learning
            - be = "be this way", "act as if you are", etc.
            - do = "do this thing", "perform this action", etc.
            - check = "check if this is true", "verify this", etc.
            """
        ),
        index=True,
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sender_id: Optional[uuid4] = Field(default=None, index=True, nullable=True)
    receiver_id: Optional[uuid4] = Field(default=None, index=True, nullable=True)
    parent_id: Optional[uuid4] = Field(
        default=None, index=True, nullable=True, foreign_key="messages.id"
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

    state: "DurableAgentState" = Relationship(
        back_populates="agent", sa_relationship_args={"lazy": "join"}
    )
    messages_sent: list[DurableMessage] = Relationship(
        back_populates="sender",
        sa_relationship_kwargs={"lazy": "select"},
        foreign_key="messages.sender_id",
    )
    messages_received: list[DurableMessage] = Relationship(
        back_populates="receiver",
        sa_relationship_kwargs={"lazy": "select"},
        foreign_key="messages.receiver_id",
    )


class DurableAgentState(AbstractDurableObject):
    """Use to store agent state"""

    __tablename__ = "states"

    agent_id: UUID4 = Field(
        index=True, foreign_key="agents.id", sa_column_kwargs={"nullable": False}
    )
    agent: DurableAgent = Relationship(
        back_populates="state", sa_relationship_args={"lazy": "select"}
    )


DurableAgent.update_forward_refs()
DurableMessage.update_forward_refs()
