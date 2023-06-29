from llambdao.base import GroupChatNode, Message, Node, SwarmNode


class TestNode(Node):
    role = "assistant"

    def receive(self, message: Message):
        if not message.content.endswith("!!"):
            yield self.reply_to(message, content=f"{message.content}!")


def test_swarm_node():
    a = TestNode()
    b = TestNode()
    c = TestNode()
    swarm = SwarmNode([a, b, c])
    m = Message(content="test", role="user", sender_id=a.id, type="request")

    messages = list(swarm.do(m))
    assert len(messages) == 3

    assert messages[0].content == "test!"
    assert messages[0].sender_id == a.id

    assert messages[1].content == "test!"
    assert messages[1].sender_id == b.id

    assert messages[2].content == "test!"
    assert messages[2].sender_id == c.id


def test_group_chat_node():
    a = TestNode()
    b = TestNode()
    c = TestNode()
    group = GroupChatNode([a, b, c])
    m = Message(content="test", role="user", sender_id=b.id, type="chat")

    messages = list(group.receive(m))
    assert len(messages) == 6

    assert messages[0].content == "test!"
    assert messages[0].sender_id == a.id

    assert messages[1].content == "test!"
    assert messages[1].sender_id == c.id

    assert messages[2].content == "test!!"
    assert messages[2].sender_id == b.id

    assert messages[3].content == "test!!"
    assert messages[3].sender_id == c.id
    assert messages[3].sender_id == c.id

    assert messages[4].content == "test!!"
    assert messages[4].sender_id == a.id

    assert messages[5].content == "test!!"
    assert messages[5].sender_id == b.id
