from functools import cached_property
from typing import Optional

from aredis_om import Field, HashModel

from gen_net.llegos.messages import AbstractObject, Message


class AbstractRedisObject(HashModel, AbstractObject):
    @property
    def id(self):
        return self.pk


class RedisMessage(Message, AbstractRedisObject):
    sender: Optional[AbstractObject] = Field(
        default=None, alias="sender_id", index=True
    )
    receiver: Optional[AbstractObject] = Field(
        default=None, alias="receiver_id", index=True
    )
    reply_to: Optional["Message"] = Field(default=None, alias="reply_to_id", index=True)

    def __init__(self, **kwargs):
        if sender := kwargs.pop("sender", None):
            kwargs["sender_id"] = sender.id

        if receiver := kwargs.pop("receiver", None):
            kwargs["receiver_id"] = receiver.id

        if reply_to := kwargs.pop("reply_to", None):
            kwargs["reply_to_id"] = reply_to.id

        return super().__init__(**kwargs)

    @cached_property
    def sender(self):
        return self.__class__.find(self.sender_id)

    @cached_property
    def receiver(self):
        return self.__class__.find(self.receiver_id)

    @cached_property
    def reply_to(self):
        return self.__class__.find(self.reply_to_id)

    @classmethod
    @property
    def init_schema(cls):
        schema = super().init_schema
        del schema["parameters"]["pk"]
        return schema
