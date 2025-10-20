# Dexter 🤖

Dexter is an autonomous research agent that thinks, plans, and learns as it works. It performs analysis using task planning, self-reflection, and real-time web search. Think Claude Code, but built for intelligent research and information gathering.

<img width="979" height="651" alt="Screenshot 2025-10-14 at 6 12 35 PM" src="https://github.com/user-attachments/assets/5a2859d4-53cf-4638-998a-15cef3c98038" />

## Overview

Dexter takes complex questions and turns them into clear, step-by-step research plans. It runs those tasks using web search, checks its own work, and refines the results until it has a confident, data-backed answer.  

It's not just another chatbot.  It's an agent that plans ahead, verifies its progress, and keeps iterating until the job is done.

**Key Capabilities:**

- **Intelligent Task Planning**: Automatically decomposes complex queries into structured research steps
- **Autonomous Execution**: Selects and executes the right tools to gather information
- **Self-Validation**: Checks its own work and iterates until tasks are complete
- **Real-Time Web Search**: Search the internet for up-to-date information using Tavily API
- **Safety Features**: Built-in loop detection and step limits to prevent runaway execution

[![Twitter Follow](https://img.shields.io/twitter/follow/virattt?style=social)](https://twitter.com/virattt)

## Quick Start

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- OpenAI API key (get one at [platform.openai.com](https://platform.openai.com))
- Tavily API key (get one at [tavily.com](https://tavily.com))

### Installation

1. Clone the repository:

```bash
git clone https://github.com/virattt/dexter.git
cd dexter
```

2. Install dependencies with uv:

```bash
uv sync
```

3. Set up your environment variables:

```bash
# Copy the example environment file
cp env.example .env

# Edit .env and add your API keys
# OPENAI_API_KEY=your-openai-api-key
# TAVILY_API_KEY=your-tavily-api-key
```

### Usage

Run Dexter in interactive mode:

**Default version (LangChain chains):**

```bash
uv run dexter-agent
```

**LangGraph version (better scalability and control flow):**

```bash
uv run dexter-agent --use-graph
```

**With custom parameters:**

```bash
uv run dexter-agent --use-graph --max-steps 30 --max-steps-per-task 5
```

**Available flags:**

- `--use-graph`: Use LangGraph-based implementation
- `--max-steps`: Maximum number of total steps (default: 20)
- `--max-steps-per-task`: Maximum iterations per task (default: 3)

## Architecture

Dexter uses a multi-agent architecture with specialized components:

- **Planning Agent**: Analyzes queries and creates structured task lists
- **Action Agent**: Selects appropriate tools and executes research steps
- **Validation Agent**: Verifies task completion and data sufficiency
- **Answer Agent**: Synthesizes findings into comprehensive responses

## Project Structure

```skaffolding
dexter/
├── src/
│   ├── dexter/
│   │   ├── agent.py        # LangChain chains implementation (default)
│   │   ├── agent_graph.py  # LangGraph implementation (scalable)
│   │   ├── model.py        # LLM interface
│   │   ├── tools.py        # Tools
│   │   ├── prompts.py      # System prompts for each Agent
│   │   ├── schemas.py      # Pydantic models
│   │   ├── utils/          # Utility functions
│   │   └── cli.py          # CLI entry point (supports both versions)
├── AGENT_COMPARISON.md     # Detailed comparison of both implementations
├── pyproject.toml
└── uv.lock
```

## Configuration

Dexter supports configuration via command-line flags or programmatic initialization:


## How to Contribute

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

**Important**: Please keep your pull requests small and focused.  This will make it easier to review and merge.

## License

This project is licensed under the MIT License.
