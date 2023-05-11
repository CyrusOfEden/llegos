from datetime import datetime

from dotenv import load_dotenv
from faiss import IndexFlatL2
from langchain import FAISS, OpenAI
from langchain.agents import Tool
from langchain.docstore import InMemoryDocstore
from langchain.embeddings import OpenAIEmbeddings
from langchain.retrievers import TimeWeightedVectorStoreRetriever
from langchain.schema import HumanMessage
from langchain.utilities import GoogleSerperAPIWrapper, WikipediaAPIWrapper

from dao_agent.adapters.langchain import AutoGPT, AutoGPTMemory, ChatOpenAI

llm = ChatOpenAI(temperature=0)
retriever = TimeWeightedVectorStoreRetriever(
    vectorstore=FAISS(
        embedding_function=OpenAIEmbeddings().embed_query,
        index=IndexFlatL2(1536),
        docstore=InMemoryDocstore({}),
        index_to_docstore_id={},
    )
)


def test_langchain_autogpt_llambda():
    load_dotenv()

    llambda = AutoGPT.from_llm_and_tools(
        "AutoGPT",
        "Researcher",
        memory=AutoGPTMemory(retriever=retriever),
        tools=[
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
        ],
        llm=llm,
        human_in_the_loop=False,
    )
    chat_history = [
        HumanMessage(
            content="What are some 3 arrondisements in Paris to explore as a tourist?"
        )
    ]
    llambda.on("message", lambda message: chat_history.append(message))
    llambda.call.remote(chat_history=chat_history)
