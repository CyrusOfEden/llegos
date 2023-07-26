"""
**The principle of interdependent co-arizing is that all phenomena are interconnected
and mutually dependent. Everything in the universe comes into existence because of
the conditions created by other things.**

## Conversational Agents and New Models of Human-AI Computing

Most agents today have the UX of 1 human chatting with 1 agent with 1 message and 1 response,
think ChatGPT, ReAct, godmode.space and GPT4 + Code Interpreter.

My insight with github.com/shaman-ai/agent-actors was that breaking a problem down for trees
of agents to solve in parallel improved the quality of output and increased the complexity of the
task that could be accomplished. It's the same principle of chain of thoughts and tree of thoughts
applied at the agent-level rather than the token-level.

agent-actors used two types of agents: parent agents that planned, and worker agents
that executed in parallel. You could nest a parent under a parent to create infinitely deep tree of
agents that would break a problem down, solve it in parallel, and synthesize the results.

agent-actors was innovative at the time as the first open-source implementation of
parallel worker trees, but it was not without its limitations.

1. Communication was hierarchical, from parent to children
2. Communication was limited to tasks and results
3. There was no way to stream intermediate results without major refactoring of the agents.

It was as if I had created a painting, but I new I needed better paint if I wanted to
paint something even more beautiful. llm-net is the better paint.

## LLMNet: A Framework for Expressing Interconnected Networks of Agents

llm-net is a framework for expressing interconnected networks of agents.
PyTorch lets you build neural networks, LLMNet lets you build agent networks.

1. Simple: No class is more than 120 lines of code.
2. Flexible: You can use any agent implementation you want.
3. Powerful: Agents can message any other agent in the network
3. Dynamic: You can express any network of agents you want, and modify it on-the-fly.
4. Concurrent: Agents can run concurrently using coroutines, asynchronous coroutines, or actors.
5. Responsive: Intermediate messages can be yielded at any time, and execution can be interrupted.
"""


from typing import List

from openai import ChatCompletion
from pydantic import BaseModel, Field

from gen_net.agents import GenAgent, Message
from gen_net.openai import chat_messages, model_fn, parse_completion_fn_call

"""
The gateway to llm-net is the GenAgent class for agents that can send and receive messages.

For now, here's what you need to know about GenAgent:
1. Inherits from Pydantic's BaseModel
2. Has an auto-generated id of `{class_name}:{uuid}`
3. Has a metadata dict for storing arbitrary data
"""


class Assistant(GenAgent):
    role = "assistant"  # or "user", "system", used for creating messages

    completion: ChatCompletion = Field(
        default_factory=ChatCompletion,
        description="OpenAI ChatCompletion",
        exclude=True,
    )
    chat_history: List[Message] = Field(
        default_factory=list,
        description="messages prepended to ChatCompletion calls",
    )

    def inform(self, message):
        self.chat_history.append(message)


class TechnicalWriter(Assistant):
    chat_history = Field(
        default_factory=lambda: [
            Message(content="You are an expert technical writer.", role="system")
        ]
    )

    def request(self, req):
        # Can emit messages that others can listen to
        self.emit("debug", Message.reply(req, content=str(self)))

        # model_fn(type[BaseModel]) converts a Pydantic model to a JSON schema
        functions = model_fn(Message)
        # chat_messages(list[Message]) converts to JSON format
        messages = chat_messages(self.chat_history + [req])

        completion = self.completion.create(
            model="gpt-3.5-turbo-0301",
            functions=functions,
            messages=messages,
            temperature=0.3,
        )

        # _model is "Message" here
        _model, kwargs = parse_completion_fn_call(completion)

        yield Message.reply(req, **kwargs, method="response")


class TweetWriter(Assistant):
    chat_history = Field(
        default_factory=lambda: [
            Message(content="You are an expert tweet thread writer.", role="system")
        ]
    )

    # We can use Pydantic models to structure responses as data
    class TweetThread(BaseModel):
        class Tweet(BaseModel):
            content: str = Field()

        tweets: List[Tweet] = Field()

    def request(self, req):
        functions = [model_fn(self.TweetThread)]
        messages = chat_messages(self.chat_history + [req])

        completion = self.completion.create(
            model="gpt-3.5-turbo-0301",
            functions=functions,
            function_call={"name": "TweetThread"},
            messages=messages,
            temperature=0.7,
        )

        _model, kwargs = parse_completion_fn_call(completion)

        thread = self.TweetThread(**kwargs)
        # You can break up the messages you return...
        # In practice, you can yield anything. It's just a generator.
        # Chunks of responses, intermediate results, etc.
        for tweet in thread.tweets:
            yield Message.reply(req, content=tweet.content, type="response")


def test_example_assistant():
    technical = TechnicalWriter()
    # Easily hook into events
    technical.add_listener(
        "debug", lambda message: print(f"DEBUG ===================\n{message}")
    )

    tweeter = TweetWriter()
    tweeter.inform(Message(content="Be bright, concise, and interesting.", role="user"))

    technical_prompt = Message(
        content="Write a 5 paragraph summary of autonomous agents", role="user"
    )
    for writing in technical.request(technical_prompt):
        print(f"TECHNICAL WRITER =========================\n{writing} ")
        for tweet in tweeter.request(writing):
            print(f"TWEET WRITER =========================\n{tweet} ")
