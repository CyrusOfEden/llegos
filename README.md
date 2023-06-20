- [LLAMBDAO](#llambdao)
  - [The Right Abstractions](#the-right-abstractions)
  - [An Open Invitation for Collaboration](#an-open-invitation-for-collaboration)
  - [An Introduction to LLAMBDAO](#an-introduction-to-llambdao)
    - [Everything is Connected](#everything-is-connected)
    - [Generating Responses](#generating-responses)
    - [Communicating Intents](#communicating-intents)
    - [Autonomous Agents](#autonomous-agents)
    - [Nodes as Networks](#nodes-as-networks)
    - [Extending LLAMBDAO](#extending-llambdao)
    - [Humans in the Loop](#humans-in-the-loop)
  - [Conclusion](#conclusion)

# LLAMBDAO

## The Right Abstractions

When Alan Kay conceptualized Object Oriented Programming (OOP), his vision was far beyond what is predominantly practiced today. In Kay's vision, OOP was less about objects, inheritance, or encapsulation, and more about autonomous entities engaging in message-passing to get things done - a form of computational organization that mirrors the biological world.

Agent Oriented Programming (AOP) takes this core philosophy and crystallizes it, accentuating the autonomy of these interacting entities or "agents". In AOP, our focus shifts to individual agents that encapsulate state and behavior, operate autonomously, perceive their environment, and can independently chase their objectives.

Enter LLAMBDAO &mdash; Large Language Agents Modulating Behaviour in Decentralized Autonomous Organizations. LLAMBDAO is an exploration and embodiment of AOP, enabling us to frame complex systems as networks of autonomous agents communicating via messages. This closely reflects the original essence of OOP as envisaged by Alan Kay.

But here's a crucial problem that arises when we deal with complex agent architectures - the challenge of abstraction. Identifying the right abstractions is a powerful lever for productivity and robustness &mdash; it allows us to encapsulate complex ideas in a manner that's comprehensible, mutable, and extensible.

DSLs are specialized languages designed with a particular application domain in mind. By presenting the right abstractions, they streamline code writing, making it more readable, less prone to errors, and inherently expressive. LLAMBDAO's journey ventures towards establishing such a DSL for modeling agent architectures, aiming to accelerate innovation by presenting the right abstractions.

The beauty of LLAMBDAO shines in this modularity and interoperability, offering a flexible platform to model diverse autonomous agents. It promotes scalability and robustness, quintessential features needed in an open source community that deals with autonomous agents.

Embark on this journey of LLAMBDAO and witness how the essence of Object Oriented Programming transcends to align with the realm of autonomous agents, offering an enriched perspective for designing sophisticated systems. Get ready for a thrilling exploration of autonomous agents, all through the paradigm-shifting lens of LLAMBDAO!

## An Open Invitation for Collaboration

This README and the corresponding code repository are framed as an exploration, a launchpad for a journey into the vibrant landscape of autonomous agents. In the spirit of open-source and the collective advancement of knowledge, we present LLAMBDAO as a work-in-progress, rather than a final product. We invite you to join us in this exciting exploration, to push boundaries, question assumptions, and shape the future of autonomous agent architectures.

We would like to underline that the code provided here is not complete. It serves as a starting point, a conceptual framework for implementing and experimenting with the design of Large Language Agents Modulating Behaviour in Decentralized Autonomous Organizations. It's a representation of the current state of our explorations and ideas, and we fully anticipate that it will evolve and transform over time as new insights and approaches are brought to the table.

We deeply believe in the power of collaboration and the synergetic fusion of diverse perspectives. As such, we highly encourage discussions, constructive criticism, and contributions to the project. Whether you're a seasoned AI researcher, a software engineer interested in agent-oriented programming, or a passionate enthusiast eager to learn and contribute, your insights are invaluable.

In recognition of major contributions to the project, we are offering collaborator titles to those who contribute significantly to the development and expansion of LLAMBDAO. Your innovative ideas, improvements, and implementations could earn you an authorship on the future paper, acknowledging your valuable contribution to the project. This is not just an opportunity to contribute to an open-source project, but also a chance to help shape a cutting-edge field and be recognized for it.

We look forward to your participation in this journey, and can't wait to see where our collective effort and passion will take us. The future of autonomous agents awaits, and it looks brighter with every new idea and contribution. Welcome to the LLAMBDAO project!

## An Introduction to LLAMBDAO

_Large Language Agents Modulating Behaviour in Decentralized Autonomous Organizations_

The following is a fictional conversation between a Senior Engineer (SE) and a Junior Engineer (JE) introducing the concepts of LLAMBDAO.

### Everything is Connected

_SE:_ "You know how in real life, everything is connected in a way, like a web? That's what we're replicating here. Everything, every part of a system, is a Node."

_JE:_ "Like a graph?"

_SE:_ "Exactly! And they can be linked or unlinked to each other, forming a network. Let's look at the building blocks of the system &mdash; Take a peek at the code snippet."

```python
class Node(AbstractObject, ABC):
    """Nodes can be composed into graphs."""

    class Edge(AbstractObject):
        """Edges point to other nodes."""

        node: "Node" = Field()
        metadata: Optional[Metadata] = Field(default=None)
```

_JE:_ "I see. So each `Node` can have multiple `Edge`s, each of which points to another `Node`."

_SE:_ "Exactly. Now, a `Node` receives a `Message` and reacts based on the action defined in that `Message`. And `Message`s can lead to other `Message`s, forming a chain. Now take a look at `FibonacciNode`. This is a simple, computational node."

```python
class FibonacciNode(Node):
    role = "system"

    def receive(self, message):
        a, b = 0, 1
        for _ in range(int(message.content)):
            yield Message(content=str(a), sender=self)
            a, b = b, a + b
```

_JE:_ "Okay, I see. So when it receives a `Message`, it generates Fibonacci numbers up to the number in the message's content."

_SE:_ "You're getting it! And it's the same for all types of nodes. `receive` is how they respond to incoming `Message`s. What they do varies based on the node."

### Generating Responses

_SE:_ "And if you notice, the method `receive` is a generator method. This is a design choice that offers several advantages."

_JE:_ "What kind of advantages?"

_SE:_ "Well, one of the biggest advantages is it allows us to pause and resume execution as needed, providing a practical way to manage flow control within the system. By `yield`ing messages instead of simply returning them, we create an iterable series of responses rather than a single, one-off response."

_JE:_ "So this means our Node can produce a series of responses over time in response to a single message?"

_SE:_ "Yes, that's right! It's like having a conversation. When you receive a message, you don't just reply once and then stop, do you? You reply, and then based on the response you get, you might reply again, and again. That's what these nodes are doing. They're 'conversing' with each other through these iterables of messages."

_JE:_ "I see. So it's not just about returning a result, but managing an ongoing interaction. It seems like using generator functions adds a lot of flexibility to our nodes."

_SE:_ "Indeed, it does. And that's what LLAMBDAO is all about: flexibility, modularity, and scalability. By making our nodes iterable, we're making our system more adaptable and capable of handling a wide variety of use-cases."

### Communicating Intents

_SE:_ "Great! Now, let's explore the concept of messages in more depth."

_JE:_ "So we've used messages before, but only in a basic way, right?"

_SE:_ "Correct. The `Message` class has an attribute called `intent`. It dictates what kind of action the receiving node will perform. For example, a message with `intent="chat"` will trigger the `chat` method on the receiving node."

_JE:_ "That sounds powerful! And that it would lead to clean code!"

_SE:_ "Yes, it is! And here's the fun part - we have a curated set of action names that the nodes can understand, like 'chat', 'request', 'query', 'inform', 'proxy', 'step', 'be', 'do' etc. By default, nodes will dispatch messages to a method named after the action."

```python
class Message(AbstractObject):
    sender: Node = Field()
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reply_to: Optional["Message"] = Field()
    intent: Optional[str] = Field(
        description=dedent(
            """\
            A curated set of intent names to consider:
            - chat = "chat about this topic", "talk about this topic", etc.
            - request = "request this thing", "ask for this thing", etc.
            - query = "query for information"
            - inform = "inform of new data", "tell about this thing", etc.
            - proxy = "route this message to another agent"
            - step = process the environment, a la multi agent reinforcement learning
            - be = "be this way", "act as if you are", etc.
            - do = "do this thing", "perform this action", etc.
            """
        ),
    )
    content: str = Field()
```

_JE:_ "This means we can use the same message class to communicate different intents based on the `intent` attribute!"

_SE:_ "Exactly! It's a very flexible system. Remember the `receive` method in our nodes? It takes a `Message` as input and uses the `intent` attribute to determine what to do. Here, have a look:"

```python
class Node(AbstractObject, ABC):
    """Nodes can be composed into graphs."""
    ...
    def receive(self, message: "Message") -> Iterable["Message"]:
        yield from getattr(self, message.intent)(message)
```

_JE:_ "Ah, I see! So the `receive` method uses the `intent` attribute of the message to call the corresponding method on the `Node`. And these methods then generate new `Message`s."

_SE:_ "Exactly! It's like an ongoing conversation between nodes. Nodes are sending, receiving, and reacting to messages. They handle intents based on the `Message`s they receive, and these intents can lead to new `Message`s being sent. It's a cycle."

_JE:_ "That's amazing. It's like the nodes are talking to each other!"

_SE:_ "Yes, that's a great way to put it! And it's all thanks to the flexibility and power of our `Message` class. This forms the backbone of our system."

And there you have it! The concept of messages is central to how **LLAMBDAO** functions. The `intent` attribute of a `Message` directs the behavior of a `Node`, allowing for complex and flexible interactions between nodes. Now, how about you try crafting your own message and sending it to a node?

### Autonomous Agents

_SE:_ "Alright, let's move on to autonomous agents. Take a look at this `SummaryNode`. It can collect messages and generate a summary of those messages."

```python
class SummaryNode(Node):
    role = "ai"
    messages: List[Message] = Field(default_factory=list)
    summary: Optional[Message] = Field(default=None)

    def inform(self, message: Message):
        self.messages.append(message)
        self.messages = self.messages[-24:]  # keep last 24 messages

    def query(self, message: Message):
        # Generate summary
        completion = openai.ChatCompletion.create(
            messages=prepare_for_openai(messages),
            stop=["<STOP>"],
            engine="chatgpt-3.5",
        ).response.choices[0].text
        summary = Message(sender=self, content=completion)

        # Yield message
        yield summary
        # Update state
        self.summary = summary
```

_JE:_ "This is interesting! It appears we're using the OpenAI API here."

_SE:_ "Correct. In `SummaryNode`, when the node receives an `inform` message, it appends the message to its list. When it receives a `query` message, it uses the OpenAI API to summarize the last 24 messages it was informed of."

_JE:_ "I see, but what is the `prepare_for_openai` function?"

_SE:_ "Good observation. The `prepare_for_openai` function is a helper function we can import from `llambdao.openai` which transforms our `Message` objects into OpenAI-compatible dictionaries."

_JE:_ "That makes sense. And after the summary is generated, it yields a new `Message` with the summary as the content."

_SE:_ "Exactly! And it also updates its own `summary` attribute with the generated summary. It's a way for the node to keep track of its state."

_JE:_ "So it's like the node has a memory?"

_SE:_ "Exactly. And in the provided test, you can see how you might use the `SummaryNode`. You send it an `inform` message, and then you send a `query` message to generate and retrieve the summary."

_JE:_ "And the `print(response.content)` line would print the summary, right?"

_SE:_ "That's right! This `SummaryNode` is an example of an autonomous agent. It processes incoming messages and responds intelligently, using the OpenAI API."

### Nodes as Networks

_SE:_ "We've been looking at individual Nodes so far, but one of the key ideas in LLAMBDAO is that Nodes can be composed together. In other words, Nodes can act as Networks."

_JE:_ "That sounds quite fascinating. Can you show me an example of how this works?"

_SE:_ "Certainly! Let's take a look at two classes: `MapperNode` and `GroupChatNode`."

```python
class MapperNode(Node):
    def __init__(self, *nodes: Node, **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)
            node.link(self)

    def do(self, message: Message) -> Iterable[Message]:
        sender = message.sender
        yield from itertools.chain.from_iterable(
            edge.node.receive(message)
            for edge in self.edges.values()
            if edge.node != sender
        )


class GroupChatNode(MapperNode):
    def chat(self, message: Message):
        messages = [message]
        while message_i := messages.pop():
            for message_j in self.do(message):
                message_j.reply_to = message_i
                yield message_j
                messages.append(message_j)
```

_SE:_ "In the `MapperNode`, we define a node that can link with other nodes. When it does something with a message, it basically sends the message to all nodes it's linked with. `GroupChatNode` is a subclass of `MapperNode`, and it's designed to handle chat messages. When a message is sent to it, it disseminates the message to all linked nodes and iteratively processes their responses."

_JE:_ "I see. So these nodes can essentially coordinate tasks amongst each other?"

_SE:_ "Exactly! Let's introduce a practical example. Consider a philosophical round table discussion with Rumi, Lao Tzu, and Marcus Aurelius. We'll have three "PhilosopherNode"s, each representing a philosopher. The `GroupChatNode` is will allow us to pass messages between multiple nodes, in order, like a group chat."

```python
class PhilosopherNode(Node):
    role = "system"

    def chat(self, message: Message):
        # Stubbed method: it simply echoes the received message.
        yield Message(sender=self, content=message.content, action="chat", reply_to=message)

# Define our philosophers
human = ConsoleHumanNode()
rumi = PhilosopherNode(name="Rumi")
lao_tzu = PhilosopherNode(name="Lao Tzu")
marcus_aurelius = PhilosopherNode(name="Marcus Aurelius")

# Create a group chat with the philosophers
table = ConsoleGroupChatNode(human, rumi, lao_tzu, marcus_aurelius)

# User sends the first message
table.chat(
    Message(content="What is the purpose of life?", action="chat", sender=human)
)
```

_SE:_ "This uses the console helper classes. `ConsoleGroupChatNode` pretty prints every message in the group chat. `ConsoleHumanNode` allows a user to chat with the system via the console. It receives messages, pretty prints them out, and then inputs a response from the user."

```python
class ConsoleHumanNode(Node):
    role = "user"

    def chat(self, message: Message):
        pprint(message.dict())
        response = input("Enter response: ")
        yield Message(sender=self, content=response, intent="chat", reply_to=message)


class ConsoleGroupChatNode(GroupChatNode):
    role = "system"

    def __init__(self, *args, **kwargs):
        super().__init__(ConsoleHumanNode(), *args, **kwargs)

    def chat(self, message: Message):
        pprint(message.dict())
        for response in super().chat(message):
            pprint(response.dict())
```

_JE:_ "Wow, so the user can essentially join the discussion with the philosophers via the console. That's cool!"

_SE:_ "Indeed! It's all about composing Nodes together to build complex interactions. Each Node in the network acts autonomously, reacting to the messages it receives and generating responses."

_JE:_ "This really gives a new perspective on how we can structure complex systems."

_SE:_ "That's the essence of LLAMBDAO &mdash; it allows us to abstract and modularize our thinking about autonomous agents. By viewing each part as a Node or Network of Nodes, we can create complex behaviors from simple, composable elements."

### Extending LLAMBDAO

_SE:_ "Now, while our console chat is great for a quick and dirty demo, we probably want a more robust solution for actual user interactions. We could use a WebSocket handler for real-time communication with a frontend application, for example."

_JE:_ "That sounds interesting. How would that look?"

_SE:_ "Firstly, we would need a `WebSocketNode` class. This class would handle sending and receiving messages through a WebSocket connection."

```python
class WebSocketNode(Node):
    role = "system"

    def __init__(self, websocket, **kwargs):
        super().__init__(**kwargs)
        self.websocket = websocket

    def chat(self, message: Message):
        # Send message to WebSocket
        asyncio.create_task(self.websocket.send(json.dumps(message.dict())))
```

_SE:_ "This node can be part of a `GroupChatNode` just like any other node. When a `chat` message is received, it simply sends the message content over the WebSocket. This allows any connected frontend application to receive the message and display it to the user."

_JE:_ "And how would we handle user input from the frontend?"

_SE:_ "Good question! We can simply pass messages received from the WebSocket to the `GroupChatNode`. So when a user sends a message from the frontend, it's received by the WebSocket handler and then passed to the `GroupChatNode`, which disseminates it to the other nodes, including our `PhilosopherNode`s."

_JE:_ "I see. So the frontend and backend are essentially two nodes communicating with each other in the group chat."

_SE:_ "Exactly! This setup separates the user interaction logic from the backend processing logic. Each node in the system can focus on its core function, whether that's generating philosophical responses, managing the flow of messages, or handling user interactions."

_JE:_ "This makes everything so modular and maintainable. And it's all possible because we're thinking in terms of nodes and networks!"

_SE:_ "Absolutely! And that's the key advantage of this approach. The right abstractions allow us to manage complexity and create more flexible, scalable systems. By using LLAMBDAO, we're essentially speaking a Domain Specific Language for modelling agent architectures."

### Humans in the Loop

_SE:_ "So far, we've talked about how Nodes can be computational agents, like our Fibonacci or Summary nodes, or even compositions like the Group Chat Node. But what if we want to bring a human into the mix, in a way that's more convenient than the console?"

_JE:_ "That sounds like a neat idea! But how would it work?"

_SE:_ "It's quite straightforward, actually. Let's define a `HumanEmailNode`. This node has one method: `request`. When this method is invoked, it sends an email to the human agent and then waits for a reply. Once a reply is received, it yields a message with the content of the reply."

```python
import time
from email.message import EmailMessage

class HumanEmailNode(Node):
    role = "user"

    def __init__(self, domain: str, api_key: str, recipient: str, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.domain = domain
        self.recipient = recipient

    def request(self, message: Message):
        # Construct the email
        email = EmailMessage()
        email['Subject'] = message.metadata.get("subject")
        email['From'] = 'agent@llambdao.ai'
        email['To'] = self.recipient
        email.set_content(message.content)

        # Send the email using the Mailgun API
        send_response = requests.post(
            f"https://api.mailgun.net/v3/{self.domain}/messages",
            auth=("api", self.api_key),
            data=email)

        # The 'Message-ID' of the sent email will be used to match the reply
        sent_message_id = send_response.headers['Message-ID']

        # Wait for the reply
        for new_email in new_emails():
            if new_email["In-Reply-To"] == sent_message_id:
                yield Message(content=reply.content, sender=self, intent="inform")
                break
```

_JE:_ "This is fascinating! So this Node uses the email interface to interact with a human agent, but it's treated just like any other Node within our system?"

_SE:_ "Exactly! And because it's just another Node, it can be linked and composed with other Nodes as usual. This is the power of treating everything as a Node: it makes the system highly flexible and modular."

_JE:_ "I'm really starting to see the beauty of this approach!"

## Conclusion

We find ourselves at the end of this introductory exploration into LLAMBDAO, and we hope that the journey so far has inspired you to think about the structure and behavior of autonomous agents in a new light.

Through this exploration, we've unveiled the core principles behind LLAMBDAO, its theoretical foundation, and the transformative approach it brings to designing and implementing multi-agent systems. By emphasizing modularity, interoperability, and agent autonomy, LLAMBDAO opens up exciting avenues for experimentation and innovation.

Building a language to design complex systems as networks of autonomous agents is an ambitious endeavor, and while we have presented the initial scaffolding, the grandeur of the finished architecture is yet to be realized. The essence of LLAMBDAO lies not just in the code, but also in the community that will continue to shape and refine it.

It's important to remember that LLAMBDAO is not just about code; it's about a shift in perspective, a new way of conceptualizing systems and their interactions. It's an ongoing exploration that will evolve and grow richer with your insights, criticisms, and contributions. By offering you the opportunity to contribute to this project, we're not just inviting you to write code, but to be part of a larger discussion about the nature and structure of autonomous agent systems.

In conclusion, LLAMBDAO isn't the end goal, but rather, a means to an end, a tool that aids us in our journey of understanding, designing, and implementing complex autonomous systems. It encapsulates an idea, a vision that goes beyond the conventional approach, allowing us to build robust and scalable systems in a manner that is more intuitive and aligned with the way we understand the world.

We hope that you found this exploration into LLAMBDAO to be insightful, and we warmly invite you to be part of our journey. The field of autonomous agents is ripe with potential, and we believe that with LLAMBDAO, we can tap into this potential in exciting and novel ways.

Let's journey together into the vibrant landscape of autonomous agents, and collectively sculpt the future of multi-agent systems!
