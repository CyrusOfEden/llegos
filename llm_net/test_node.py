from networkx import DiGraph
from pydantic import Field

from llm_net.gen import GenAgent
from llm_net.message import UserMessage


class Questioner(GenAgent):
    question: str = Field(...)

    def chat(self, m):
        yield self.reply_to(m, content=self.question)


def test_node_graph():
    root = GenAgent()
    graph = DiGraph()
    graph.add_edges_from(
        (root, Questioner(question=q))
        for q in ["What?", "Why?", "When?", "Who?", "How?"]
    )

    gen = root.receive(UserMessage("Hello!", sender="user", method="chat"))
    assert next(gen).content == "What?"
    assert next(gen).content == "Why?"
    assert next(gen).content == "When?"
    assert next(gen).content == "Who?"
    assert next(gen).content == "How?"
