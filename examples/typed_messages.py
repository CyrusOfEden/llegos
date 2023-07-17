from llm_net.gen import GenAgent, Message


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

    def subscribe(self, message: SubscribeMessage):
        ok = True
        if not ok:
            return RefuseMessage.reply(message, "NO")

        watcher: GenAgent = message.sender
        self.on(
            "event",
            lambda content: watcher.receive(InformMessage.reply(message, content)),
        )
        return AcceptMessage.reply(message, "OK")
