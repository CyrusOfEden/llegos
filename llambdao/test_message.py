import yaml

from llambdao.message import UserMessage


def test_message_str():
    m = UserMessage(
        content="Hello, world!\nMy name is Alice!",
        from_id="alice",
        metadata={"foo": "bar"},
    )
    parsed = yaml.safe_load(str(m))
    assert m.dict() == parsed
