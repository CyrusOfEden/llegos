from datetime import datetime

import yaml
from dotenv import load_dotenv
from faiss import IndexFlatL2
from langchain import FAISS, OpenAI
from langchain.agents import Tool
from langchain.docstore import InMemoryDocstore
from langchain.embeddings import OpenAIEmbeddings
from langchain.retrievers import TimeWeightedVectorStoreRetriever
from langchain.schema import HumanMessage
from langchain.utilities import GoogleSerperAPIWrapper, WikipediaAPIWrapper

from llambdao.adapters.langchain import (
    AutoGPT,
    AutoGPTMemory,
    ChatOpenAI,
    PlanAndExecute,
    load_agent_executor,
    load_chat_planner,
)

llm = ChatOpenAI(temperature=0)
retriever = TimeWeightedVectorStoreRetriever(
    vectorstore=FAISS(
        embedding_function=OpenAIEmbeddings().embed_query,
        index=IndexFlatL2(1536),
        docstore=InMemoryDocstore({}),
        index_to_docstore_id={},
    )
)


def test_langchain_autogpt():
    agent = AutoGPT.from_llm_and_tools(
        "AutoGPT",
        "Researcher",
        memory=AutoGPTMemory(retriever=retriever),
        tools=test_toolkit(),
        llm=llm,
        human_in_the_loop=False,
    )
    chat_history = [
        HumanMessage(
            content="What are some 3 arrondisements in Paris to explore as a tourist?"
        )
    ]
    agent.on("message", lambda message: chat_history.append(message))
    agent.request(chat_history=chat_history)


def test_langchain_plan_and_execute():
    PlanAndExecute(
        directive=yaml.dump(
            {
                "name": "PlanAndExecuteActor",
                "description": "A bot that plans and executes a series of steps.",
                "abilities": ["expert planner", "expert executor"],
            }
        ),
        actor_options={
            "max_concurrency": 1,
        },
        tools=test_toolkit(),
        planner=load_chat_planner(llm),
        executer=load_agent_executor(llm, tools=test_toolkit(), verbose=True),
    )


def test_toolkit():
    load_dotenv()
    return [
        Tool(
            name="Generative LLM",
            func=OpenAI(temperature=0.75).__call__,
            description=(
                "A generative large language model, useful for generating text "
                "or efficiently getting a surface-level understanding of a topic. "
                "You will want to confirm the information with a more reliable source. "
                "The input is a prompt for the large language model."
            ),
        ),
        Tool(
            name="Wikipedia",
            func=WikipediaAPIWrapper().run,
            description=(
                "A wrapper around Wikipedia that fetches page summaries. "
                "Useful when you need a summary of a topic, such as a "
                "person, place, company, historical event. Input is the topic."
            ),
        ),
        Tool(
            name="Search",
            func=GoogleSerperAPIWrapper().run,
            description=(
                "Google, useful for up up-to-date information from the internet. "
                "Input should be a search query."
            ),
        ),
        Tool(
            name="DateTime",
            func=lambda _: datetime.utcnow().isoformat(),  # noqa: F821
            description="Useful for when you want to know the current date and time.",
        ),
    ]
