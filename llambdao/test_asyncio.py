import pytest

from llambdao.asyncio import AsyncGroupChatNode, AsyncNode, AsyncSwarmNode, Message


class AsyncTestNode(AsyncNode):
    role = "assistant"

    async def areceive(self, message: Message):
        if not message.content.endswith("!!"):
            yield self.reply_to(message, content=f"{message.content}!")


@pytest.mark.asyncio
async def test_mapper_node():
    a = AsyncTestNode()
    b = AsyncTestNode()
    c = AsyncTestNode()
    swarm = AsyncSwarmNode([a, b, c])

    messages = []
    async for m in swarm.areceive(
        Message(type="do", content="test", sender_id="pytest", role="user")
    ):
        messages.append(m)

    assert len(messages) == 3

    assert messages[0].content == "test!"
    assert messages[0].sender_id == a.id

    assert messages[1].content == "test!"
    assert messages[1].sender_id == b.id

    assert messages[2].content == "test!"
    assert messages[2].sender_id == c.id


@pytest.mark.asyncio
async def test_group_chat_node():
    a = AsyncTestNode()
    b = AsyncTestNode()
    c = AsyncTestNode()
    group = AsyncGroupChatNode([a, b, c])

    messages = []
    async for m in group.areceive(
        Message(content="test", sender_id=b.id, role="user", type="chat")
    ):
        messages.append(m)

    assert len(messages) == 6

    assert messages[0].content == "test!"
    assert messages[0].sender_id == a.id

    assert messages[1].content == "test!"
    assert messages[1].sender_id == c.id

    assert messages[2].content == "test!!"
    assert messages[2].sender_id == b.id

    assert messages[3].content == "test!!"
    assert messages[3].sender_id == c.id

    assert messages[4].content == "test!!"
    assert messages[4].sender_id == a.id

    assert messages[5].content == "test!!"
    assert messages[5].sender_id == b.id
