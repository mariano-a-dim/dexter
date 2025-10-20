"""
LangGraph-based Agent implementation.

This is a parallel implementation to agent.py that uses LangGraph for better scalability,
explicit state management, and clearer control flow.
"""

from typing import List, TypedDict, Annotated, Literal
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from dexter.model import llm
from dexter.prompts import (
    ACTION_SYSTEM_PROMPT,
    ANSWER_SYSTEM_PROMPT,
    PLANNING_SYSTEM_PROMPT,
    VALIDATION_SYSTEM_PROMPT,
)
from dexter.schemas import Answer, IsDone, Task, TaskList
from dexter.tools import TOOLS
from dexter.utils.logger import Logger
from dexter.utils.ui import show_progress


# ============================================================================
# STATE DEFINITION
# ============================================================================

class AgentGraphState(TypedDict):
    """State for the agent graph."""
    query: str  # Original user query
    tasks: List[Task]  # List of planned tasks
    current_task_idx: int  # Index of the current task being executed
    session_outputs: List[str]  # Accumulated outputs from all tool executions
    answer: str  # Final answer
    current_task_result: dict  # Result from current task execution


# ============================================================================
# GRAPH NODES
# ============================================================================

class AgentGraph:
    def __init__(self, max_steps: int = 20, max_steps_per_task: int = 3):
        self.logger = Logger()
        self.max_steps = max_steps
        self.max_steps_per_task = max_steps_per_task
        
        # Create task executor
        self.task_executor = self._create_task_executor()
        
        # Build the graph
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile()

    def _create_task_executor(self) -> AgentExecutor:
        """Create AgentExecutor for executing tasks with tools."""
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", ACTION_SYSTEM_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        agent = create_tool_calling_agent(llm, TOOLS, prompt_template)
        
        return AgentExecutor(
            agent=agent,
            tools=TOOLS,
            verbose=False,
            max_iterations=self.max_steps_per_task,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )

    # ------------------------------------------------------------------------
    # NODE: Planner
    # ------------------------------------------------------------------------
    
    @show_progress("Planning tasks...", "Tasks planned")
    def planner_node(self, state: AgentGraphState) -> AgentGraphState:
        """Plan tasks based on the user query."""
        query = state["query"]
        
        try:
            tool_descriptions = "\n".join([f"- {t.name}: {t.description}" for t in TOOLS])
            system_prompt = PLANNING_SYSTEM_PROMPT.format(tools=tool_descriptions)
            
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("user", "Given the user query: '{query}', create a list of tasks to be completed.")
            ])
            
            planning_chain = prompt_template | llm.with_structured_output(TaskList)
            response = planning_chain.invoke({"query": query})
            tasks = response.tasks
        except Exception as e:
            self.logger._log(f"Planning failed: {e}")
            tasks = [Task(id=1, description=query, done=False)]
        
        task_dicts = [task.model_dump() for task in tasks]
        self.logger.log_task_list(task_dicts)
        
        return {
            **state,
            "tasks": tasks,
            "current_task_idx": 0,
            "session_outputs": []
        }

    # ------------------------------------------------------------------------
    # NODE: Executor
    # ------------------------------------------------------------------------
    
    def executor_node(self, state: AgentGraphState) -> AgentGraphState:
        """Execute the current task using tools."""
        tasks = state["tasks"]
        current_idx = state["current_task_idx"]
        session_outputs = state.get("session_outputs", [])
        
        if current_idx >= len(tasks):
            return state
        
        current_task = tasks[current_idx]
        
        if current_task.done:
            return {
                **state,
                "current_task_idx": current_idx + 1
            }
        
        self.logger.log_task_start(current_task.description)
        
        try:
            # Execute task with AgentExecutor
            context_str = "\n".join(session_outputs[-5:]) if session_outputs else "No previous context."
            
            input_text = f"""Task: {current_task.description}
            
Previous context:
{context_str}

Complete this task using the available tools."""
            
            result = self.task_executor.invoke({"input": input_text})
            
            # Collect outputs from intermediate steps
            new_outputs = []
            if result.get("intermediate_steps"):
                for action, observation in result["intermediate_steps"]:
                    tool_name = action.tool
                    tool_input = action.tool_input
                    self.logger.log_tool_run(tool_name, str(observation)[:100])
                    new_outputs.append(f"Tool: {tool_name}\nInput: {tool_input}\nOutput: {observation}")
            
            return {
                **state,
                "session_outputs": session_outputs + new_outputs,
                "current_task_result": result
            }
            
        except Exception as e:
            self.logger._log(f"Task execution failed: {e}")
            return {
                **state,
                "current_task_result": {"error": str(e)}
            }

    # ------------------------------------------------------------------------
    # NODE: Validator
    # ------------------------------------------------------------------------
    
    @show_progress("Validating...", "")
    def validator_node(self, state: AgentGraphState) -> AgentGraphState:
        """Validate if the current task is complete."""
        tasks = state["tasks"]
        current_idx = state["current_task_idx"]
        session_outputs = state.get("session_outputs", [])
        
        if current_idx >= len(tasks):
            return state
        
        current_task = tasks[current_idx]
        
        try:
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", VALIDATION_SYSTEM_PROMPT),
                ("user", "Task: '{task}'\n\nTool outputs:\n{results}\n\nIs the task done?")
            ])
            
            validation_chain = prompt_template | llm.with_structured_output(IsDone)
            response = validation_chain.invoke({
                "task": current_task.description,
                "results": "\n".join(session_outputs)
            })
            
            if response.done:
                current_task.done = True
                self.logger.log_task_done(current_task.description)
                
        except Exception as e:
            self.logger._log(f"Validation failed: {e}")
            # Mark as done to avoid infinite loops
            current_task.done = True
        
        # Move to next task
        return {
            **state,
            "current_task_idx": current_idx + 1
        }

    # ------------------------------------------------------------------------
    # NODE: Answerer
    # ------------------------------------------------------------------------
    
    @show_progress("Generating answer...", "Answer ready")
    def answerer_node(self, state: AgentGraphState) -> AgentGraphState:
        """Generate final answer based on all collected data."""
        query = state["query"]
        session_outputs = state.get("session_outputs", [])
        
        all_results = "\n\n".join(session_outputs) if session_outputs else "No data was collected."
        
        try:
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", ANSWER_SYSTEM_PROMPT),
                ("user", "Original user query: '{query}'\n\nData collected from tools:\n{results}\n\nProvide a comprehensive answer.")
            ])
            
            answer_chain = prompt_template | llm.with_structured_output(Answer)
            response = answer_chain.invoke({
                "query": query,
                "results": all_results
            })
            answer = response.answer
        except Exception as e:
            self.logger._log(f"Answer generation failed: {e}")
            answer = "Unable to generate answer due to an error."
        
        self.logger.log_summary(answer)
        
        return {
            **state,
            "answer": answer
        }

    # ------------------------------------------------------------------------
    # ROUTING FUNCTIONS
    # ------------------------------------------------------------------------
    
    def should_continue_after_planning(self, state: AgentGraphState) -> Literal["executor", "answerer"]:
        """Decide if we should execute tasks or answer directly."""
        tasks = state.get("tasks", [])
        
        if not tasks or len(tasks) == 0:
            return "answerer"
        
        return "executor"
    
    def should_continue_after_validation(self, state: AgentGraphState) -> Literal["executor", "answerer"]:
        """Decide if we should execute next task or generate answer."""
        current_idx = state["current_task_idx"]
        tasks = state["tasks"]
        
        # If we've processed all tasks, generate answer
        if current_idx >= len(tasks):
            return "answerer"
        
        # Otherwise, execute next task
        return "executor"

    # ------------------------------------------------------------------------
    # GRAPH CONSTRUCTION
    # ------------------------------------------------------------------------
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        workflow = StateGraph(AgentGraphState)
        
        # Add nodes
        workflow.add_node("planner", self.planner_node)
        workflow.add_node("executor", self.executor_node)
        workflow.add_node("validator", self.validator_node)
        workflow.add_node("answerer", self.answerer_node)
        
        # Set entry point
        workflow.set_entry_point("planner")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "planner",
            self.should_continue_after_planning,
            {
                "executor": "executor",
                "answerer": "answerer"
            }
        )
        
        # After executor, always validate
        workflow.add_edge("executor", "validator")
        
        # After validator, decide next step
        workflow.add_conditional_edges(
            "validator",
            self.should_continue_after_validation,
            {
                "executor": "executor",
                "answerer": "answerer"
            }
        )
        
        # After answerer, end
        workflow.add_edge("answerer", END)
        
        return workflow

    # ------------------------------------------------------------------------
    # PUBLIC API (compatible with original Agent)
    # ------------------------------------------------------------------------
    
    def run(self, query: str) -> str:
        """
        Execute the agent using LangGraph.
        
        This method maintains the same API as the original Agent.run() 
        for easy interchangeability.
        """
        initial_state = AgentGraphState(
            query=query,
            tasks=[],
            current_task_idx=0,
            session_outputs=[],
            answer="",
            current_task_result={}
        )
        
        # Run the graph
        final_state = self.compiled_graph.invoke(initial_state)
        
        return final_state["answer"]

