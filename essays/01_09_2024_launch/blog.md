# Llegos: A strongly-typed Python DSL for multi-agent systems

![An image of a techno-wizard in a flowing robe adorned with digital runes, with interconnected glowing orbs floating about. One orb contains a coiling snake, another a majestic parrot, and another a serene llama. All the orbs emit intense, glowing power. Streams of light intertwine seamlessly in front of the wizard's focused eyes, casting intricate shadows and illuminating the wizard's face with a mysterious light.](../../wizard.png)

> This research was spearheaded by [Cyrus](https://x.com/CyrusOfEden), our resident expert in multi-agent systems, as [an act of devotion](https://www.youtube.com/watch?v=YPytyPQ8HdI). He's been working on this project for a while now, and we're excited to share it with you.

!!!!!! INTRO VIDEO !!!!!!!

*"More of a PyTorch, less of a Keras"*

We're excited to unveil the alpha release of Llegos, a Python DSL to catalyze innovation in multi-agent systems research and development.

## Exploring the Design Space of Multi-Agent Systems with Llegos

Recent advances in multi-agent systems have opened up a world of possibilities for developers. But with these new opportunities come new challenges. How do you design a multi-agent system that's flexible, adaptable, and scalable? How do you ensure that your system can handle the complexity of real-world interactions?

We recognize that we're still early in the journey of multi-agent systems. Projects like AutoGen, CamelAI, BabyAGI, and CrewAI have explored the uncharted waters of multi-agent systems. Llegos helps researchers navigate this uncharted territory by offering an expressive domain-specific language for implementing multi-agent interactions, so we can design innovative solutions to complex problems.

Existing approaches offer a limited view of multi-agent systems. They focus on specific implementations of multi-agent systems, rather than providing a framework for building multi-agent systems. Llegos empowers developers with elegant building blocks to forge their own paths in the design space of multi-agent systems. This flexibility is crucial in a field as dynamic and diverse as multi-agent systems, where one size seldom fits all, and best practices have yet to be discovered.

Whether it's simulating complex ecosystems, orchestrating intricate interactions, or developing advanced coordination protocols, Llegos provides the foundational elements and freedom necessary for such endeavors. Llegos is paint, not paintings.

You only need these 2 sentences to get an intuitive understanding of Llegos:

1. **llegos.Actors are a container for your agents.**
2. **"llegos.Actors send llegos.Messages and share llegos.Objects in llegos.Scenes."**

## Key Features of Llegos

1. **Strongly typed message passing:** At the heart of Llegos is its use of Pydantic models for message passing. This ensures precision and clarity in communication, allowing for dynamically generated, well-structured messages crucial for complex multi-agent interactions.

2. **Messaging with email semantics** Llegos introduces an intuitive, email-like messaging system. Messages have parents, enabling functionalities like replying and forwarding, which enhances clarity and traceability in the system's communication.

3. **Bring your own libraries:** Whether that's Langchain, LlamaIndex, CamelAI, transformers... use Llegos Actors to elevate your agents into a multi-agent system, and coordinate them using a Scene.

4. **Flexibility and generalizability:** Llegos Scenes are themselves Actors, and can be nested within each other. This allows for the creation of complex, multi-layered environments where different groups of actors can interact within their sub-contexts.

## Get Started with Llegos

Eager to start your journey with Llegos? Check out our [Github repo](https://github.com/CyrusOfEden/llegos) and begin exploring the unlimited potential of multi-agent systems. We're particularly curious to see how you'll use Llegos to explore the design space of multi-agent systems, and will be highlighting some of the most innovative projects on our [Twitter](https://twitter.com/CyrusOfEden).

## The Future of Llegos

The alpha release is just the beginning of our journey with Llegos. As the community grows and the project evolves, we look forward to expanding its capabilities and integrating user feedback.

We're particularly excited to work with explorers like you to discover new ways of using Llegos. We believe that Llegos can be a catalyst for innovation in multi-agent systems, and we're excited to see what you create with it. Come join us in our [Discord](https://discord.gg/jqVphNsB4H), and let's build the future of multi-agent systems together.

## FAQ

**Q: What is the difference between Llegos and other multi-agent systems like AutoGen, CamelAI, ChatDev, Agent Actors?**

All those works are innovating in their own right as implementations of different interaction paradigms. Llegos is unique in that it makes it easier for you to explore the design space of interaction paradigms, rather than offering you ready-built paradigms. It is a framework for building multi-agent systems, rather than configuring a specific multi-agent system. It is paint, not a painting.

**Q: How does Llegos relate to libraries like Langchain, LlamaIndex, Outlines, DSPy, Instructor?**

Llegos is a framework for building multi-agent systems, and it is designed to be flexible and generalizable, and it is not tied to any specific way of calling LLMs. Any combination of libraries in any order can be used in the implementation of your Llegos Actors, however you please.
