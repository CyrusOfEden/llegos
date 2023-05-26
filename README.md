**Simple to start. Powerful for production**

## TODO

1. Write langchain tests
2. Write asyncio tests
3. Write ray tests

## Quick Start

### Langchain

It all starts with a `Node`. Nodes are classes that compose programs into a network.

Every node can receive messages.

```python
# Langchain imports
from langchain.chat_models import ChatOpenAI()
from langchain.experimental.autonomous_agents.autogpt import AutoGPT

# ==================================
# Nodes communicate through Messages
# ==================================
from llambdao import Node, Message
# Standard implementations for langchain autonomous agents
from llambdao.langchain import AutoGPTNode

vectorstore=FAISS(
    embedding_function=OpenAIEmbeddings().embed_query,
    index=IndexFlatL2(1536),
    docstore=InMemoryDocstore({}),
    index_to_docstore_id={},
)

# Just wrap the langchain in a Node
node = AutoGPTNode(chain=AutoGPT.from_llm_and_tools(
    "AutoGPT",
    "Researcher",
    memory=AutoGPTMemory(retriever=SelfQueryRetriever(vectorstore=vectorstore)),
    tools=test_toolkit(include=[
        NodeTool(
            plan_and_execute_node,
            description="an agent that can plan and execute on a high-level task"
        )
    ]),
    llm=llm,
    human_in_the_loop=False,
))

# Nodes can receive information (to add it to its vectorstore)
node.receive(Message.inform("The answer is to life, the universe, and everything is 42."))

# Nodes can respond to requests
response = node.receive(
    Message.request("What is the answer to life, the universe, and everything?")
)
```

Well, what do Nodes and Messages look like? A Node is essentially an interface. And with Messages, your Nodes can talk.

```python
from pydantic import DataModel, Field

class Node(DataModel):
    class Edge(DataModel):
        node: "Node" = Field()
        metadata: Metadata = Field(default_factory=dict)

    name: str = Field(default_factory=lambda: str(uuid4()))
    edges: Dict[str, Edge] = Field(default_factory=dict)

    def receive(self, message: Message) -> Optional[Message]:
        return getattr(self, message.action)(message)


class Message(DataModel):
    body: str = Field(description="message contents")
    sender: Optional[str] = Field(description="sender identifier")
    recipient: Optional[str] = Field(description="recipient identifier")
    thread: Optional[str] = Field(default=None, description="conversation identifier")
    metadata: Metadata = Field(default_factory=dict, description="additional metadata")

    @classmethod
    def inform(cls, body: str, **kwargs):
        """Create an inform message."""
        metadata = {**kwargs.pop("metadata", {}), "action": "inform"}
        return cls(**kwargs, body=body, metadata=metadata)

    @classmethod
    def request(cls, body: str, **kwargs):
        """Create a request message."""
        metadata = {**kwargs.pop("metadata", {}), "action": "request"}
        return cls(**kwargs, body=body, metadata=metadata)

    @classmethod
    def reply_to(
        cls, to_message: "Message", with_body: str, and_metadata: Optional[Metadata] = None
    ):
        """Create a reply to a message."""
        if and_metadata is not None:
            and_metadata.update(to_message.metadata)

        and_metadata.update(to_message.metadata)
        return cls(
            to=to_message.sender,
            sender=to_message.recipient,
            body=with_body,
            thread=to_message.thread,
            metadata=and_metadata,
        )
```

