import pytest

from llambdao.node.asyncio import AsyncGroupChatNode, AsyncMapperNode, Message, Node


class AsyncTestNode(Node):
    role = "assistant"

    async def achat(self, message: Message):
        if not message.content.endswith("!!"):
            yield Message(sender=self, content=message.content + "!")


@pytest.mark.asyncio
async def test_mapper_node():
    a = AsyncTestNode()
    b = AsyncTestNode()
    c = AsyncTestNode()
    mapper = AsyncMapperNode([a, b, c])
    m = Message(sender=AsyncTestNode(), content="test", kind="chat")

    assert list(await mapper.areceive(m)) == [
        Message(sender=a, content="test!"),
        Message(sender=b, content="test!"),
        Message(sender=c, content="test!"),
    ]


@pytest.mark.asyncio
async def test_group_chat_node():
    a = AsyncTestNode()
    b = AsyncTestNode()
    c = AsyncTestNode()
    group = AsyncGroupChatNode([a, b, c])
    m = Message(sender=b, content="test", kind="chat")

    assert list(await group.areceive(m)) == [
        Message(sender=a, content="test!"),
        Message(sender=c, content="test!"),
        Message(sender=b, content="test!!"),
        Message(sender=c, content="test!!"),
    ]
