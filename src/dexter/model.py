import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel
from typing import Type, List, Optional, Any, Iterator, Dict
from langchain_core.tools import BaseTool
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGenerationChunk

from dexter.prompts import DEFAULT_SYSTEM_PROMPT

# Custom ChatOpenAI that completely disables streaming
class ChatOpenAINoStreaming(ChatOpenAI):
    """ChatOpenAI wrapper that completely disables streaming for models that require organization verification."""
    
    def __init__(self, **kwargs):
        # Force streaming to False
        kwargs['streaming'] = False
        super().__init__(**kwargs)
    
    def stream(self, *args, **kwargs) -> Iterator[BaseMessage]:
        """Override stream to prevent streaming - falls back to invoke."""
        result = self.invoke(*args, **kwargs)
        yield result
    
    def _stream(self, *args, **kwargs) -> Iterator[ChatGenerationChunk]:
        """Override _stream to prevent streaming at a lower level."""
        raise NotImplementedError("Streaming is disabled for this model")

# Initialize the OpenAI client
# Make sure your OPENAI_API_KEY is set in your environment
# Using ChatOpenAINoStreaming to completely prevent streaming with models that require verification
llm = ChatOpenAINoStreaming(
    model="gpt-5", 
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
