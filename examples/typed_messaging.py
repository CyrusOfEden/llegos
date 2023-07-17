from typing import Callable

from llm_net.gen import Field, GenAgent, Message


class SubscribeMessage(Message):
    method = "subscribe"


class InformMessage(Message):
    method = "inform"


class AcceptMessage(Message):
    method = "accept"


class RefuseMessage(Message):
    method = "refuse"


class EventAgent(GenAgent):
    role = "assistant"
    subscriptions: dict[Message, Callable] = Field(default_factory=dict)

    def subscribe(self, message: Message):
        ok = True
        if ok:
            watcher: GenAgent = message.sender
            handler = self.on(
                "event",
                lambda content: watcher.receive(InformMessage.reply(message, content)),
            )
            self.subscriptions[message] = handler
            return AcceptMessage.reply(message, "OK")
        else:
            return RefuseMessage.reply(message, "NO")

    def unsubscribe(self, message: Message):
        sub = message.reply_to
        if sub in self.subscriptions:
            self.remove_listener("event", self.subscriptions[sub])
            return InformMessage.reply(message, "OK")
