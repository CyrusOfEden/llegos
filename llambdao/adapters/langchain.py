from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain.callbacks.manager import CallbackManagerForChainRun
from langchain.chat_models import ChatOpenAI  # noqa: F401
from langchain.experimental.autonomous_agents.autogpt.agent import FINISH_NAME
from langchain.experimental.autonomous_agents.autogpt.agent import (
    AutoGPT as LangchainAutoGPT,
)
from langchain.experimental.plan_and_execute import (
    PlanAndExecute as LangchainPlanAndExecute,
)
from langchain.experimental.plan_and_execute import load_agent_executor  # noqa F401
from langchain.experimental.plan_and_execute import load_chat_planner  # noqa F401
from langchain.schema import AIMessage, Document, HumanMessage, SystemMessage
from pydantic import ValidationError

from llambdao.agent import AbstractAgent, AgentRequest, AgentResponse


class PlanAndExecute(LangchainPlanAndExecute, AbstractAgent):
    def inform(self, params: AgentRequest) -> None:
        raise NotImplementedError

    def request(self, params: AgentRequest) -> AgentResponse:
        raise NotImplementedError

    def _call(
        self,
        inputs: Dict[str, Any],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Dict[str, Any]:
        plan = self.planner.plan(
            inputs,
            callbacks=run_manager.get_child() if run_manager else None,
        )
        if run_manager:
            self.emit("plan", str(plan))
            run_manager.on_text(str(plan), verbose=self.verbose)
        for step in plan.steps:
            _new_inputs = {"previous_steps": self.step_container, "current_step": step}
            new_inputs = {**_new_inputs, **inputs}
            response = self.executer.step(
                new_inputs,
                callbacks=run_manager.get_child() if run_manager else None,
            )
            self.emit("step", step, response)
            if run_manager:
                run_manager.on_text(
                    f"*****\n\nStep: {step.value}", verbose=self.verbose
                )
                run_manager.on_text(
                    f"\n\nResponse: {response.response}", verbose=self.verbose
                )
            self.step_container.add_step(step, response)

        return {self.output_key: self.step_container.get_final_response()}


class AutoGPT(LangchainAutoGPT, AbstractAgent):
    def inform(self, params: AgentRequest) -> None:
        raise NotImplementedError

    def request(self, params: AgentRequest) -> AgentResponse:
        raise NotImplementedError

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
                    return AgentResponse(response=self.full_message_history[-1])

                memory_to_add += feedback

            self.memory.add_documents([Document(page_content=memory_to_add)])
            self.full_message_history.append(SystemMessage(content=result))
            self.emit("message", SystemMessage(content=result))
            self.full_message_history.append(SystemMessage(content=result))
            self.emit("message", SystemMessage(content=result))
            self.full_message_history.append(SystemMessage(content=result))
            self.emit("message", SystemMessage(content=result))
