from typing import Optional

from redis_om import JsonModel

from llm_net.abstract import AbstractObject
from llm_net.gen import Field, Message


class AbstractRedisObject(JsonModel, AbstractObject):
    @property
    def id(self):
        return self.pk


class RedisMessage(Message, AbstractRedisObject):
    sender: Optional[str] = Field(default=None, alias="sender_id", index=True)
    receiver: Optional[str] = Field(default=None, alias="receiver_id", index=True)
    reply_to: Optional[str] = Field(default=None, alias="reply_to_id", index=True)

    @property
    def sender(self):
        return self.__class__.find(self.sender_id)

    @property
    def receiver(self):
        return self.__class__.find(self.receiver_id)

    @property
    def reply_to(self):
        return self.__class__.find(self.reply_to_id)

    @classmethod
    @property
    def init_fn(cls):
        schema = super().init_fn
        del schema["parameters"]["pk"]
        return schema
