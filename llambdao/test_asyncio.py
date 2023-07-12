import httpx
import pytest

from llambdao.asyncio import AsyncApplicatorNode, AsyncGroupChatNode, AsyncNode, Message


class AsyncWebsiteSnippetNode(AsyncNode):
    role = "system"

    async def arequest(self, message: Message):
        async with httpx.AsyncClient() as client:
            response = await client.get(message.content)
            yield self.reply_to(message, response.text[:280])


@pytest.mark.asyncio
async def test_website_summary_node():
    snipper = AsyncWebsiteSnippetNode()

    request = Message(
        type="request",
        content="https://openai.com/blog/function-calling-and-other-api-updates",
        from_id="pytest",
        role="user",
    )
    async for snippet in snipper.areceive(request):
        assert snippet.content.startswith("<!DOCTYPE html>")


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
    swarm = AsyncApplicatorNode([a, b, c])

    messages = []
    async for m in swarm.areceive(
        Message(type="do", content="test", from_id="pytest", role="user")
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
        Message(content="test", from_id=b.id, role="user", type="chat")
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
