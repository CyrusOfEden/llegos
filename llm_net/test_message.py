import yaml

from llm_net import message


def test_message_str():
    m = message.UserMessage(
        content="Hello, world!\nMy name is Alice!",
        method="chat",
        sender="alice",
        metadata={"foo": "bar"},
    )
    parsed = yaml.safe_load(str(m))
    assert m.dict() == parsed


def test_message_graph():
    m1 = message.UserMessage(
        content="Hello, world!\nMy name is Alice!",
        method="chat",
        sender="alice",
    )
    m2 = message.UserMessage(
        content="Hello, Alice!",
        method="chat",
        sender="bob",
        reply_to=m1.id,
    )
    m3 = message.UserMessage(
        content="Hello, Bob!",
        method="chat",
        sender="alice",
        reply_to=m2.id,
    )
    g = message.message_graph([m1, m2, m3])
    assert g.has_predecessor(m2, m1)
    assert g.has_predecessor(m3, m2)
