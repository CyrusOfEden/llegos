import yaml

from llambdao.message import UserMessage


def test_message_str():
    m = UserMessage(content="Hello, world!\nMy name is Alice!", sender_id="alice")
    parsed = yaml.safe_load(str(m))
    assert m.dict() == parsed
