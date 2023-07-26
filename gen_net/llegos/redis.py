from redis_om import JsonModel

from gen_net.llegos.messages import AbstractObject, Message


class AbstractRedisObject(JsonModel, AbstractObject):
    @property
    def id(self):
        return self.pk


class RedisMessage(Message, AbstractRedisObject):
    def __init__(self, **kwargs):
        if sender := kwargs.pop("sender", None):
            kwargs["sender_id"] = sender.id

        if receiver := kwargs.pop("receiver", None):
            kwargs["receiver_id"] = receiver.id

        if reply_to := kwargs.pop("reply_to", None):
            kwargs["reply_to_id"] = reply_to.id

        return super().__init__(**kwargs)

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
    def init_schema(cls):
        schema = super().init_schema
        del schema["parameters"]["pk"]
        return schema
