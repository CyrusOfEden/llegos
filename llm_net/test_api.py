import json
from os import environment as env

from fastapi import FastAPI, WebSocket
from upstash_redis.asyncio import Redis

from llm_net.asyncio.gen import AsyncGenAgent
from llm_net.message import Message

redis = Redis(url=env["UPSTASH_REDIS_REST_URL"], token=env["UPSTASH_REDIS_REST_TOKEN"])


def agent_app(id: str) -> FastAPI:
    app = FastAPI()

    @app.websocket("/connect")
    async def connect(ws: WebSocket, token: str):
        await ws.accept()

        data = await redis.get(id)
        agent = AsyncGenAgent(**json.loads(data))

        while message := Message(**ws.receive_json()):
            async for response in agent.areceive(message):
                await ws.send_json(response.dict())

        await redis.set(id, agent.json())

    return app
