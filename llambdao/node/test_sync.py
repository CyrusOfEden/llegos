from llambdao.node.sync import GroupChatNode, MapperNode, Message, Node


class TestNode(Node):
    role = "assistant"

    def chat(self, message: Message):
        if not message.content.endswith("!!"):
            yield Message(sender=self, content=message.content + "!")


def test_mapper_node():
    a = TestNode()
    b = TestNode()
    c = TestNode()
    mapper = MapperNode([a, b, c])
    m = Message(sender=TestNode(), content="test")

    assert list(mapper.chat(m)) == [
        Message(sender=a, content="test!"),
        Message(sender=b, content="test!"),
        Message(sender=c, content="test!"),
    ]


def test_group_chat_node():
    a = TestNode()
    b = TestNode()
    c = TestNode()
    group = GroupChatNode([a, b, c])
    m = Message(sender=b, content="test")

    assert list(group.chat(m)) == [
        Message(sender=a, content="test!"),
        Message(sender=c, content="test!"),
        Message(sender=b, content="test!!"),
        Message(sender=c, content="test!!"),
    ]
