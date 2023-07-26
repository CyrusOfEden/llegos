from gen_net.llegos.asyncio import propogate_all
from gen_net.llegos.networks import AsyncGenAgent, Field, GenNetwork, Message
from gen_net.messages import messages_list


class ChatMessage(Message):
    method = "chat"


class Participant(AsyncGenAgent):
    greeted: set[AsyncGenAgent] = Field(default_factory=set, exclude=True)

    async def chat(self, message: ChatMessage):
        if message.sender in self.greeted:
            raise StopAsyncIteration

        chat_history = messages_list(message, 12)
        print(chat_history)

        yield ChatMessage.reply(
            sender=self,
            receiver=message.sender,
            body=f"Hello, {message.sender}! I am {self}.",
        )


class Conversation(GenNetwork):
    participants: list[Participant] = Field(min_items=2)

    async def chat(self, message: ChatMessage):
        messages = [
            ChatMessage.forward(message, sender=self, receiver=p)
            for p in self.participants
        ]
        async for reply in propogate_all(messages):
            if (yield reply) is StopAsyncIteration:
                break
