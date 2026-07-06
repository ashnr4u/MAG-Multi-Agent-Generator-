from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv

load_dotenv()

#the structure of the data
class AgentState(TypedDict):
    request: str
    tasks: List[str]
    current_task: int
    results: Dict[str, Any]
    errors: List[str]
    final_output: str


class SimpleAgent:
    # Initializes the AI models, configures the workflow, and prepares the agent for execution.
    def __init__(self, model_name="openai/gpt-oss-120b"):
        self.llm = ChatGroq(
            temperature=0.7,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name=model_name
        )

        self.summarizer_llm = ChatGroq(
            temperature=0.3,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name=model_name
        )

        #context limit exceeded so add to prevents token explosion
        self.MAX_TASK_OUTPUT_CHARS = 2500  

        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()

    # ---------------- WORKFLOW ---------------- #

    def _build_workflow(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("planner", self.plan_tasks)
        workflow.add_node("executor", self.execute_task)
        workflow.add_node("summarizer", self.summarize_results)

        workflow.set_entry_point("planner")

        workflow.add_edge("planner", "executor")
        
        # Dynamically decides whether to continue executing tasks or move to the summarizer.
        workflow.add_conditional_edges(
            "executor",
            self.should_continue,
            {
                "executor": "executor",
                "summarizer": "summarizer",
            },
        )

        workflow.add_edge("summarizer", END)

        return workflow

    def should_continue(self, state: AgentState) -> str:
        return "executor" if state["current_task"] < len(state["tasks"]) else "summarizer"

    # ---------------- PLANNER ---------------- #
    
    def plan_tasks(self, state: AgentState) -> AgentState:
        request = state.get("request", "")

        prompt = ChatPromptTemplate.from_messages([
            ("system",
            "Break the request into 3-5 short, actionable tasks. "
            "Each task must be one line only."),
            ("user", request)
        ])

        chain = prompt | self.llm

        # Retry planner once if it fails to generate valid tasks
        max_attempts = 2

        for attempt in range(max_attempts):
            try:
                response = chain.invoke({})
            except Exception as e:
                return {
                    "request": request,
                    "tasks": [],
                    "current_task": 0,
                    "results": {},
                    "errors": [f"Planner error: {str(e)}"],
                    "final_output": (
                        "The planner failed due to an API or model error. "
                        "Please try again."
                    )
                }

            tasks = [
                t.strip("-• ").strip()
                for t in response.content.split("\n")
                if len(t.strip()) > 5
            ][:5]

            if tasks:
                break

        else:
            # Executed only if both attempts failed
            return {
                "request": request,
                "tasks": [],
                "current_task": 0,
                "results": {},
                "errors": ["Planner failed to generate tasks after retry."],
                "final_output": (
                    "Unable to generate a task plan. "
                    "Please try rephrasing your request."
                )
            }

        return {
            "request": request,
            "tasks": tasks,
            "current_task": 0,
            "results": {},
            "errors": [],
            "final_output": ""  # Empty string - will be filled by summarizer
        }

    # ---------------- EXECUTOR ---------------- #

    def execute_task(self, state: AgentState) -> AgentState:
        tasks = state["tasks"]
        i = state["current_task"]

        if i >= len(tasks):
            return state

        task = tasks[i]
        request = state["request"]

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "Complete the task concisely. "
             "Max 200-300 words. No large tables."),
            ("user", f"Task: {task}\nContext: {request}")
        ])

        chain = prompt | self.llm
        try:
            response = chain.invoke({})
            result = response.content[:self.MAX_TASK_OUTPUT_CHARS]
        except Exception as e:
            result = f"Task failed: {str(e)}"
            state["errors"].append(
                f"Task {i + 1} ({task}): {str(e)}"
            )

        state["results"][f"task_{i}"] = {
            "task": task,
            "result": result
        }

        return {
            **state,
            "current_task": i + 1
        }

    # ---------------- SUMMARIZER ---------------- #

    def summarize_results(self, state: AgentState) -> AgentState:
        if not state["tasks"]:
            # No tasks completed - return error state
            return {
                **state,
                "final_output": "No tasks were generated. Please try again with a clearer request."
            }
        
        tasks = state["tasks"]
        results = state["results"]

        combined = "\n".join([
            f"Task: {tasks[i]}\n{results[f'task_{i}']['result']}"
            for i in range(len(tasks))
        ])

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "Convert the content into a concise professional document. "
             "Remove repetition. Keep it under 800-1200 words."),
            ("user", combined)
        ])

        chain = prompt | self.summarizer_llm
        try:
            response = chain.invoke({})
            final_output = response.content[:8000]
        except Exception as e:
            state["errors"].append(f"Summarizer error: {str(e)}")
            # Fall back to the raw combined results
            final_output = combined

        return {
            **state,
            "final_output": final_output
        }

    # ---------------- ENTRY ---------------- #

    def process_request(self, request: str) -> AgentState:
        initial_state = AgentState(
            request=request,
            tasks=[],
            current_task=0,
            results={},
            errors=[],
            final_output=""
        )

        return self.app.invoke(initial_state)