from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv

load_dotenv()


class SimpleAgent:
    def __init__(self, model_name="openai/gpt-oss-120b"):
        self.llm = ChatGroq(
            temperature=0.7,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name=model_name
        )

        # 🔥 NEW: small summarizer model (prevents TPM overflow)
        self.summarizer_llm = ChatGroq(
            temperature=0.3,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name=model_name
        )

        self.MAX_TASK_OUTPUT_CHARS = 2500  # prevents token explosion

        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()

    # ---------------- WORKFLOW ---------------- #

    def _build_workflow(self):
        workflow = StateGraph(dict)

        workflow.add_node("planner", self.plan_tasks)
        workflow.add_node("executor", self.execute_task)
        workflow.add_node("summarizer", self.summarize_results)

        workflow.set_entry_point("planner")

        workflow.add_edge("planner", "executor")

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

    def should_continue(self, state: Dict):
        return "executor" if state["current_task"] < len(state["tasks"]) else "summarizer"

    # ---------------- PLANNER ---------------- #

    def plan_tasks(self, state: Dict) -> Dict:
        request = state.get("request", "")

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "Break the request into 3-5 short, actionable tasks. "
             "Each task must be one line only."),
            ("user", request)
        ])

        chain = prompt | self.llm
        response = chain.invoke({})

        tasks = [
            t.strip("-• ").strip()
            for t in response.content.split("\n")
            if len(t.strip()) > 5
        ][:5]

        return {
            "request": request,
            "tasks": tasks,
            "current_task": 0,
            "results": {},
            "errors": []
        }

    # ---------------- EXECUTOR ---------------- #

    def execute_task(self, state: Dict) -> Dict:
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
        response = chain.invoke({})

        # 🔥 NEW: hard trim to avoid token explosion
        result = response.content[:self.MAX_TASK_OUTPUT_CHARS]

        state["results"][f"task_{i}"] = {
            "task": task,
            "result": result
        }

        return {
            **state,
            "current_task": i + 1
        }

    # ---------------- SUMMARIZER ---------------- #

    def summarize_results(self, state: Dict) -> Dict:
        tasks = state["tasks"]
        results = state["results"]

        combined = "\n".join([
            f"Task: {tasks[i]}\n{results[f'task_{i}']['result']}"
            for i in range(len(tasks))
        ])

        # 🔥 NEW: chunk-safe summarization prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "Convert the content into a concise professional document. "
             "Remove repetition. Keep it under 800-1200 words."),
            ("user", combined)
        ])

        chain = prompt | self.summarizer_llm
        response = chain.invoke({})

        return {
            **state,
            "final_output": response.content[:8000]  # safety cap
        }

    # ---------------- ENTRY ---------------- #

    def process_request(self, request: str) -> Dict[str, Any]:
        initial_state = {
            "request": request,
            "tasks": [],
            "current_task": 0,
            "results": {},
            "errors": [],
            "final_output": ""
        }

        return self.app.invoke(initial_state)