from __future__ import annotations

from typing import List

from langchain.chat_models import ChatOpenAI  # noqa: F401
from langchain.experimental.autonomous_agents.autogpt.agent import FINISH_NAME
from langchain.experimental.autonomous_agents.autogpt.agent import (
    AutoGPT as LangchainAutoGPT,
)
from langchain.schema import AIMessage, Document, HumanMessage, SystemMessage
from pydantic import ValidationError

from dao_agent.agent import AbstractAgent, AgentResponse

# noqa F401 => easier imports, better developer experience


class AutoGPT(LangchainAutoGPT, AbstractAgent):
    def run(self, goals: List[str]) -> AgentResponse:
        user_input = (
            "Determine which next command to use, "
            "and respond using the format specified above:"
        )
        self.full_message_history.append(HumanMessage(content=user_input))

        # Interaction Loop
        loop_count = 0
        while True:
            # Discontinue if continuous limit is reached
            loop_count += 1

            # Send message to AI, get response
            assistant_reply = self.chain.run(
                goals=goals,
                messages=self.full_message_history,
                memory=self.memory,
                user_input=user_input,
            )

            # Print Assistant thoughts
            print(assistant_reply)
            self.full_message_history.append(AIMessage(content=assistant_reply))
            self.emit("message", AIMessage(content=assistant_reply))

            # Get command name and arguments
            action = self.output_parser.parse(assistant_reply)
            tools = {t.name: t for t in self.tools}
            if action.name == FINISH_NAME:
                return action.args["response"]
            if action.name in tools:
                tool = tools[action.name]
                try:
                    observation = tool.run(action.args)
                    self.emit("action:observation", action, observation)
                except ValidationError as e:
                    observation = (
                        f"Validation Error in args: {str(e)}, args: {action.args}"
                    )
                except Exception as e:
                    self.emit("action:error", action, e)
                    observation = (
                        f"Error: {str(e)}, {type(e).__name__}, args: {action.args}"
                    )
                result = f"Command {tool.name} returned: {observation}"
            elif action.name == "ERROR":
                result = f"Error: {action.args}. "
            else:
                result = (
                    f"Unknown command '{action.name}'. "
                    f"Please refer to the 'COMMANDS' list for available "
                    f"commands and only respond in the specified JSON format."
                )

            memory_to_add = (
                f"Assistant Reply: {assistant_reply} " f"\nResult: {result} "
            )
            if self.feedback_tool is not None:
                feedback = f"\n{self.feedback_tool.run('Input: ')}"
                if feedback in {"q", "stop"}:
                    print("EXITING")
                    self.emit("exit", "human:exit")
                    return self.full_message_history[-1]

                memory_to_add += feedback

            self.memory.add_documents([Document(page_content=memory_to_add)])
            self.full_message_history.append(SystemMessage(content=result))
            self.emit("message", SystemMessage(content=result))
