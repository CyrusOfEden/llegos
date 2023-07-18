# llm_net

Welcome to llm_net, a toolkit for building advanced autonomous agent systems!

If Langchain is like a microwave, then llm_net is like a professional gas stove. llm_net is:

1. Simple: No class is more than 120 lines of code.
2. Flexible: You can use any agent implementation you want.
3. Powerful: Combine agents together into multi-agent systems
4. Concurrent: Agents can run concurrently using coroutines, asynchronous coroutines, or actors.
5. Responsive: Agents can emit messages to be listened to.

Instead of giving you out-of-the-box agents, llm_net provides you with the structure to develop your own autonomous agents with rich behaviors. When you want to get fancy, llm_net helps you make the next BabyAGI, AutoGPT, or multi-modal, multi-agent system.

## Gen(erative)Agents and Messages

At the heart of llm_net's design is the notion of flexibility and adaptability. llm_net introduces the notion of [Gen(erative)Agents](./llm_net/gen.py) that communicate with [Messages](./llm_net/message.py). These two primitives make llm_net a powerful tool for building intricate multi-agent systems, where individual agents can vary from simple task handlers to complex conversational AIs.

GenAgents are provide a starting point for implementing your own custom agents, and include useful functionality for developer experience. First, they know how to receive Messages. Second, they act as an EventEmitter, allowing you to `self.emit(name, *args, **kwargs)` intermediate values from your methods. This is particularly useful when you want to stream chunks to a frontend, or add instrumentation without cluttering your logic.

The Message class forms the foundation of inter-agent communication within llm_net. Each message object transports information, requests, or commands from one agent to another, enabling a rich, multi-threaded dialogue to develop within a network of agents. Messages are more than just data carriers; they are dynamic tools of communication that foster collaboration and coordination among agents.

The combination of GenAgent and Message provides a solid basis for constructing a variety of multi-agent architectures. Whether you aim to create a simple linear conversation flow or an intricate network of interacting agents, llm_net's architecture offers the flexibility and power to realize your vision. This design philosophy dovetails with our belief in building adaptable and extensible systems.

## Examples & Quick-Start

[examples/quickstart.py](./examples/quickstart.py) shows how GenAgent composes openai.ChatCompletion and agent state. If you're familiar with Langchain or other agent frameworks, then think of GenAgent as the agent that uses different sub-agents to accomplish a variety of tasks.

An example of a more complex interaction can be found in [examples/contract_net.py](./examples/contract_net.py), where a Manager agents receives a task, calls for proposals from a group of Contractors, reviews them, ultimately accepting one to delegate the task to.

## Contribution

Contributions to llm_net are welcome and greatly appreciated. We believe that the community's collective wisdom and creativity will enable us to build a more powerful and flexible tool. If you're interested in contributing, here are some guidelines:

1. **Issues**: Feel free to submit issues regarding bugs, feature requests, or other areas of concern. We value your feedback and will do our best to respond in a timely manner.

2. **Code**: If you're interested in adding a feature or fixing a bug, please start by submitting an issue. Once we've had a chance to discuss your proposal, you can make a pull request with your changes.

3. **Documentation**: Clear and comprehensive documentation makes any project more accessible. If you notice an area of the documentation that could be improved, or if you want to create new tutorials or guides, we would love your help.

## Future Work

As llm_net is still in its early stages, there are many exciting directions for future development. Here are some areas we're particularly interested in:

1. **Autonomous Agent Architectures**: We're interested in developers like you creating your own agent architectures with llm_net and are happy to feature your repository.
1. **Expanded Communication Protocols**: While llm_net currently supports simple message passing, we're interested in adding more advanced communication protocols. This might include negotiation protocols, voting mechanisms, or more complex dialogue management strategies.
3. **Integration with Other Libraries**: llm_net is designed to be flexible and adaptable. We're interested in making it easy to integrate llm_net with other popular machine learning, natural language processing, and agent-based modeling libraries.

We're excited to see where the community takes llm_net, and we look forward to collaborating with you!

