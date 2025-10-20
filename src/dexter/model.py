import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel
from typing import Type, List, Optional
from langchain_core.tools import BaseTool
from langchain_core.messages import AIMessage

from dexter.prompts import DEFAULT_SYSTEM_PROMPT

# Configure LangSmith if credentials are available
if os.getenv("LANGSMITH_API_KEY"):
    os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING", "true")
    os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "dexter-default")

# Initialize the OpenAI client
llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0, 
    api_key=os.getenv("OPENAI_API_KEY")
)

def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    output_schema: Optional[Type[BaseModel]] = None,
    tools: Optional[List[BaseTool]] = None,
) -> AIMessage:
  final_system_prompt = system_prompt if system_prompt else DEFAULT_SYSTEM_PROMPT
  
  prompt_template = ChatPromptTemplate.from_messages([
      ("system", final_system_prompt),
      ("user", "{prompt}")
  ])

  runnable = llm
  if output_schema:
      runnable = llm.with_structured_output(output_schema)
  elif tools:
      runnable = llm.bind_tools(tools, parallel_tool_calls=False)
  
  chain = prompt_template | runnable
  return chain.invoke({"prompt": prompt})
