import yaml

from gpt_net import message


def test_message_str():
    m = message.UserMessage(
        content="Hello, world!\nMy name is Alice!",
        type="chat",
        from_id="alice",
        metadata={"foo": "bar"},
    )
    parsed = yaml.safe_load(str(m))
    assert m.dict() == parsed


def test_message_graph():
    m1 = message.UserMessage(
        content="Hello, world!\nMy name is Alice!",
        type="chat",
        from_id="alice",
    )
    m2 = message.UserMessage(
        content="Hello, Alice!",
        type="chat",
        from_id="bob",
        reply_to_id=m1.id,
    )
    m3 = message.UserMessage(
        content="Hello, Bob!",
        type="chat",
        from_id="alice",
        reply_to_id=m2.id,
    )
    g = message.compose_graph([m1, m2, m3])
    assert g.has_predecessor(m2, m1)
    assert g.has_predecessor(m3, m2)
