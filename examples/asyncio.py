import asyncio

import httpx

from llambdao.asyncio import AsyncNode
from llambdao.message import Message


class AsyncWebsiteSnippetNode(AsyncNode):
    role = "system"

    async def arequest(self, message: Message):
        async with httpx.AsyncClient() as client:
            urls = message.content.split("\n")
            futures = [client.get(url) for url in urls]
            async for text in asyncio.gather(*futures):
                snippet = text[:280]
                yield Message(sender_id=self, content=snippet, parent_id=message)


async def test_website_summary_node():
    snipper = AsyncWebsiteSnippetNode()

    request = Message(
        content="https://openai.com/blog/function-calling-and-other-api-updates",
        type="request",
    )
    async for snippet in snipper.areceive(request):
        print(snippet.content)
