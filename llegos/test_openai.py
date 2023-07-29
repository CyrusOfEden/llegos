from openai import ChatCompletion

from llegos.asyncio import EphemeralMessage, Field
from llegos.conversations import ConversationalAgent
from llegos.messages import message_chain
from llegos.openai import prepare_async_call


class Chatter(ConversationalAgent):
    completion: ChatCompletion = Field(default_factory=ChatCompletion)

    async def converse(self, message: EphemeralMessage):
        messages, functions, call_function = prepare_async_call(
            message_chain(message, height=12),
            llegos=[EphemeralMessage, ContractNet(manager, contractors)],
        )
        completion = self.completion.create(
            messages=messages, functions=functions, temperature=0.8, max_tokens=250
        )
        async for reply in call_function(completion):
            yield reply
