from openai import ChatCompletion

from gen_net.llegos.asyncio import Field, Message
from gen_net.llegos.conversations import ConversationalAgent
from gen_net.llegos.openai import prepare_async_function_call
from gen_net.messages import messages_iter


class Chatter(ConversationalAgent):
    completion: ChatCompletion = Field(default_factory=ChatCompletion)

    async def converse(self, message: Message):
        messages, functions, call_function = prepare_async_function_call(
            messages_iter(message, count=12),
            llegos=[Message],
        )
        completion = self.completion.create(messages=messages, functions=functions)
        async for reply in call_function(completion):
            yield reply
