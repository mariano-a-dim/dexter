from typing import List
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableSequence
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from dexter.model import call_llm, llm
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


class Agent:
    def __init__(self, max_steps: int = 20, max_steps_per_task: int = 3):
        self.logger = Logger()
        self.max_steps = max_steps
        self.max_steps_per_task = max_steps_per_task
        
        # Create planning chain using LangChain
        self.planning_chain = self._create_planning_chain()
        
        # Create answer generation chain using LangChain
        self.answer_chain = self._create_answer_chain()
        
        # Create validation chain using LangChain
        self.validation_chain = self._create_validation_chain()
        
        # Create AgentExecutor for task execution
        self.task_executor = self._create_task_executor()

    def _create_planning_chain(self) -> RunnableSequence:
        """Create a LangChain chain for task planning."""
        tool_descriptions = "\n".join([f"- {t.name}: {t.description}" for t in TOOLS])
        system_prompt = PLANNING_SYSTEM_PROMPT.format(tools=tool_descriptions)
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "Given the user query: '{query}', create a list of tasks to be completed.")
        ])
        
        return prompt_template | llm.with_structured_output(TaskList)
    
    def _create_answer_chain(self) -> RunnableSequence:
        """Create a LangChain chain for answer generation."""
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", ANSWER_SYSTEM_PROMPT),
            ("user", "Original user query: '{query}'\n\nData collected from tools:\n{results}\n\nProvide a comprehensive answer.")
        ])
        
        return prompt_template | llm.with_structured_output(Answer)
    
    def _create_validation_chain(self) -> RunnableSequence:
        """Create a LangChain chain for task validation."""
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", VALIDATION_SYSTEM_PROMPT),
            ("user", "Task: '{task}'\n\nTool outputs:\n{results}\n\nIs the task done?")
        ])
        
        return prompt_template | llm.with_structured_output(IsDone)
    
    def _create_task_executor(self) -> AgentExecutor:
        """Create AgentExecutor for executing tasks with tools using tool calling."""
        # Tool calling agent prompt - uses ACTION_SYSTEM_PROMPT for consistency
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", ACTION_SYSTEM_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Use create_tool_calling_agent - modern approach that uses native tool calling
        agent = create_tool_calling_agent(llm, TOOLS, prompt_template)
        
        return AgentExecutor(
            agent=agent,
            tools=TOOLS,
            verbose=False,
            max_iterations=self.max_steps_per_task,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )

    # ---------- task planning ----------
    @show_progress("Planning tasks...", "Tasks planned")
    def plan_tasks(self, query: str) -> List[Task]:
        """Plan tasks using LangChain chain."""
        try:
            response = self.planning_chain.invoke({"query": query})
            tasks = response.tasks
        except Exception as e:
            self.logger._log(f"Planning failed: {e}")
            tasks = [Task(id=1, description=query, done=False)]
        
        task_dicts = [task.model_dump() for task in tasks]
        self.logger.log_task_list(task_dicts)
        return tasks

    # ---------- task validation ----------
    @show_progress("Validating...", "")
    def validate_task(self, task_desc: str, results: str) -> bool:
        """Validate if task is complete using LangChain chain."""
        try:
            response = self.validation_chain.invoke({
                "task": task_desc,
                "results": results
            })
            return response.done
        except Exception as e:
            self.logger._log(f"Validation failed: {e}")
            return False

    # ---------- main loop ----------
    def run(self, query: str):
        """Execute the agent using LangChain's AgentExecutor."""
        session_outputs = []

        # Plan tasks using LangChain chain
        tasks = self.plan_tasks(query)

        # If no tasks, answer directly
        if not tasks:
            answer = self._generate_answer(query, session_outputs)
            self.logger.log_summary(answer)
            return answer

        # Execute each task using AgentExecutor
        for task in tasks:
            if task.done:
                continue
                
            self.logger.log_task_start(task.description)
            
            try:
                # Use AgentExecutor to handle the task
                result = self._execute_task_with_agent(task.description, session_outputs)
                
                # Collect outputs from intermediate steps
                if result.get("intermediate_steps"):
                    for action, observation in result["intermediate_steps"]:
                        tool_name = action.tool
                        tool_input = action.tool_input
                        self.logger.log_tool_run(tool_name, str(observation)[:100])
                        session_outputs.append(f"Tool: {tool_name}\nInput: {tool_input}\nOutput: {observation}")
                
                # Validate task completion
                if self.validate_task(task.description, "\n".join(session_outputs)):
                    task.done = True
                    self.logger.log_task_done(task.description)
                    
            except Exception as e:
                self.logger._log(f"Task execution failed: {e}")
                # Mark as done to avoid infinite loops
                task.done = True

        # Generate final answer using LangChain chain
        answer = self._generate_answer(query, session_outputs)
        self.logger.log_summary(answer)
        return answer
    
    def _execute_task_with_agent(self, task_description: str, context: list) -> dict:
        """Execute a single task using AgentExecutor."""
        context_str = "\n".join(context[-5:]) if context else "No previous context."
        
        input_text = f"""Task: {task_description}
        
Previous context:
{context_str}

Complete this task using the available tools."""
        
        result = self.task_executor.invoke({"input": input_text})
        return result
    
    # ---------- answer generation ----------
    @show_progress("Generating answer...", "Answer ready")
    def _generate_answer(self, query: str, session_outputs: list) -> str:
        """Generate answer using LangChain chain."""
        all_results = "\n\n".join(session_outputs) if session_outputs else "No data was collected."
        
        try:
            response = self.answer_chain.invoke({
                "query": query,
                "results": all_results
            })
            return response.answer
        except Exception as e:
            self.logger._log(f"Answer generation failed: {e}")
            return "Unable to generate answer due to an error."
