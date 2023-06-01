from datetime import datetime

from dotenv import load_dotenv
from faiss import IndexFlatL2
from langchain import FAISS, OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.docstore import InMemoryDocstore
from langchain.embeddings import OpenAIEmbeddings
from langchain.experimental.autonomous_agents import AutoGPT, BabyAGI
from langchain.experimental.plan_and_execute import (
    PlanAndExecute,
    load_agent_executor,
    load_chat_planner,
)
from langchain.tools import Tool
from langchain.utilities import GoogleSerperAPIWrapper, WikipediaAPIWrapper
from langchain.vectorstores.base import VectorStoreRetriever

from llambdao import Message
from llambdao.langchain import AutoGPTNode, BabyAGINode, NodeTool, PlanAndExecuteNode

load_dotenv()


chat_llm = ChatOpenAI(temperature=0, verbose=True)
vectorstore = FAISS(
    embedding_function=OpenAIEmbeddings().embed_query,
    index=IndexFlatL2(1536),
    docstore=InMemoryDocstore({}),
    index_to_docstore_id={},
)
tools = [
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
        func=lambda _: datetime.utcnow().isoformat(),
        description="Useful for when you want to know the current date and time.",
    ),
]
plan_and_execute_node = PlanAndExecuteNode(
    chain=PlanAndExecute(
        planner=load_chat_planner(chat_llm),
        executor=load_agent_executor(chat_llm, tools=tools, verbose=True),
    ),
)


def test_langchain_babyagi():
    node = BabyAGINode(
        chain=BabyAGI.from_llm(
            chat_llm,
            vectorstore=vectorstore,
        )
    )
    node.receive(
        Message.query(
            "Give me a summary of the latest 3 memecoins and common themes in their strategy."
        )
    )


def test_langchain_autogpt():
    """
    An agent with 3 cognitive layers: AutoGPT, Plan, and Execute

    AutoGPT runs the outermost cognitive loop,
    which can then call the PlanAndExecuteNote as a tool,
    which in turn internally runs the executor.
    """

    node = AutoGPTNode(
        chain=AutoGPT.from_llm_and_tools(
            "AutoGPT",
            "Researcher",
            memory=VectorStoreRetriever(vectorstore=vectorstore),
            tools=[
                *tools,
                NodeTool(
                    node=plan_and_execute_node,
                    description=(
                        "an AI agent that can plan and execute on a high-level task "
                        "with access to several tools, such as the internet."
                    ),
                ),
            ],
            llm=chat_llm,
            human_in_the_loop=False,
        ),
    )
    node.receive(
        Message.query(
            "Give me a summary of the latest 3 memecoins and common themes in their strategy."
        )
    )
