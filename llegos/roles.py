from llegos.ephemeral import EphemeralAgent


class AssistantAgent(EphemeralAgent):
    """Helper class for nodes whose messages should be set to role = assistant."""

    role = "assistant"


class SystemAgent(EphemeralAgent):
    """Helper class for nodes whose messages should be set to role = system."""

    role = "system"
