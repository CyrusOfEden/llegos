from typing import AsyncIterable, List

from pyee.asyncio import AsyncIOEventEmitter

from llambdao.base import Field, GraphNode, Message, Node, SystemNode


class AsyncNode(Node):
    event_emitter: AsyncIOEventEmitter = Field(
        default_factory=AsyncIOEventEmitter, init=False
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_emitter = AsyncIOEventEmitter()

    async def areceive(self, message: Message):
        method = getattr(self, "a" + message.type, None)
        if not method:
            raise AttributeError(
                f"{self.__class__.__name__} does not have a method named {message.type}"
            )

        async for response in method(message):
            yield response


class AsyncGraphNode(GraphNode, AsyncNode):
    pass


class AsyncApplicatorNode(SystemNode, AsyncNode):
    def __init__(self, nodes: List[Node], **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)

    async def ado(self, message: Message) -> AsyncIterable[Message]:
        for edge in self.edges.values():
            async for response in edge.node.areceive(message):
                yield response


class AsyncGroupChatNode(SystemNode, AsyncNode):
    def __init__(self, nodes: List[Node], **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)

    async def achat(self, message: Message):
        messages = [message]
        cursor = 0
        while cursor < len(messages):
            message_i = messages[cursor]
            for edge in self.edges.values():
                if edge.node.id == message_i.sender_id:
                    continue
                async for message_j in edge.node.areceive(message_i):
                    yield message_j
                    messages.append(message_j)
            cursor += 1
