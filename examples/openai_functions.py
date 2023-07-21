from langchain.utilities import GoogleSerperAPIWrapper
from pydantic import Field

from llm_net.openai import (
    GenAgent,
    Message,
    OpenAIAgent,
    chat_messages,
    model_fn,
    parse_completion_fn_call,
)


class SerperAgent(GenAgent):
    client: GoogleSerperAPIWrapper = Field(
        default_factory=GoogleSerperAPIWrapper,
        description="Google Serper API Wrapper",
        exclude=True,
    )

    class QueryMessage(Message):
        method = "query"
        body: str = Field(description="Google query string")

    messages = [QueryMessage]

    def query(self, message: QueryMessage):
        result = self.client.run(str(message.body))
        yield Message.reply(message, result)


class ChatMessage(Message):
    role = "assistant"
    method = "chat"
    body: str = Field(description="Message to respond to the user with")


class ExecutiveAgent(OpenAIAgent):
    serper: SerperAgent = Field(
        default_factory=SerperAgent,
        description="Google Serper Agent",
        exclude=True,
    )

    def request(self, message: Message):
        completion = self.completion.create(
            messages=chat_messages(
                [Message(role="system", content="You are a researcher."), message]
            ),
            functions=[self.serper.call_fn, model_fn(ChatMessage)],
        )
        fn, kwargs = parse_completion_fn_call(completion)

        if fn == "SerperAgent":
            yield from self.serper.receive(
                SerperAgent.QueryMessage.reply(message, **kwargs)
            )
        elif fn == "ChatMessage":
            yield self.draft_message(**kwargs, method="chat")
