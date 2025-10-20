import argparse
import os
from dotenv import load_dotenv

# Load environment variables BEFORE importing any dexter modules
load_dotenv()

from dexter.agent import Agent
from dexter.agent_graph import AgentGraph
from dexter.utils.intro import print_intro
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Dexter - AI Research Agent")
    parser.add_argument(
        "--use-graph",
        action="store_true",
        help="Use LangGraph-based agent (better scalability and control flow)"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum number of steps for the agent (default: 20)"
    )
    parser.add_argument(
        "--max-steps-per-task",
        type=int,
        default=3,
        help="Maximum number of steps per task (default: 3)"
    )
    args = parser.parse_args()
    
    print_intro()
    
    # Show LangSmith status
    if os.getenv("LANGSMITH_API_KEY"):
        project = os.getenv("LANGSMITH_PROJECT", "dexter-default")
        print(f"📊 LangSmith tracing enabled: Project '{project}'")
        print(f"   View traces at: https://smith.langchain.com/o/default/projects/p/{project}\n")
    
    # Show Tavily search limit if configured
    tavily_limit = os.getenv("TAVILY_MAX_SEARCHES_PER_SESSION")
    if tavily_limit:
        print(f"🔍 Tavily search limit: {tavily_limit} searches per session")
        print(f"   (Useful for managing free tier quota)\n")
    
    # Choose agent implementation based on flag
    if args.use_graph:
        print("🔷 Using LangGraph-based agent (enhanced scalability)\n")
        agent = AgentGraph(
            max_steps=args.max_steps,
            max_steps_per_task=args.max_steps_per_task
        )
    else:
        print("🔹 Using LangChain chains agent (default)\n")
        agent = Agent(
            max_steps=args.max_steps,
            max_steps_per_task=args.max_steps_per_task
        )

    # Create a prompt session with history support
    session = PromptSession(history=InMemoryHistory())

    while True:
        try:
            query = session.prompt(">> ")
            if query.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
            if query:
                agent.run(query)
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
