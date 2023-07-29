from llegos.ephemeral import EphemeralMessage
from llegos.messages import message_list


class TestMessageList:
    def test_replies(self):
        m1 = EphemeralMessage(body="Initial message", intent="chat")
        m2 = EphemeralMessage(body="First reply", reply_to=m1, intent="chat")
        m2_1 = EphemeralMessage(body="Second reply", reply_to=m2, intent="chat")
        m2_2 = EphemeralMessage(body="Third reply", reply_to=m2, intent="chat")

        assert message_list(m2_1) == [m1, m2, m2_1]
        assert message_list(m2_2, height=2) == [m2, m2_2]
