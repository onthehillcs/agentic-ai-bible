# The Agentic AI Bible — Companion Code Repository

This repository contains all code examples, exercise solutions, and supplementary
materials for *The Agentic AI Bible* (Revised & Expanded Edition, 2026)
by Jordan Caldwell.

## Repository Structure

```
.
├── chapters/
│   ├── ch01/   # Chapter 1: What Is an Agent?
│   ├── ch02/   # Chapter 2: A Brief History of Autonomous Systems
│   ├── ch03/   # Chapter 3: The Agent Loop
│   ├── ch04/   # Chapter 4: The Research Agent
│   ├── ch05/   # Chapter 5: LLMs as Reasoning Engines
│   ├── ch06/   # Chapter 6: Tool Use and Function Calling
│   ├── ch07/   # Chapter 7: Memory
│   ├── ch08/   # Chapter 8: Planning and Decomposition
│   ├── ch09/   # Chapter 9: Model Context Protocol (MCP)
│   ├── ch10/   # Chapter 10: Single-Agent Patterns
│   ├── ch11/   # Chapter 11: Multi-Agent Systems
│   ├── ch12/   # Chapter 12: Human-in-the-Loop
│   ├── ch13/   # Chapter 13: Long-Running Agents
│   ├── ch14/   # Chapter 14: Observability and Evaluation
│   ├── ch15/   # Chapter 15: Safety and Guardrails
│   ├── ch16/   # Chapter 16: Security
│   ├── ch17/   # Chapter 17: Cost and Performance
│   ├── ch18/   # Chapter 18: Deployment and SRE
│   ├── ch19/   # Chapter 19: Computer-Use Agents
│   ├── ch20/   # Chapter 20: Coding Agents
│   └── ch21/   # Chapter 21: Case Studies
├── appendix_d/ # Appendix D: Production Research Agent
├── resources/  # Shared utilities, prompts, helpers
├── .github/
│   └── workflows/
│       └── ci.yml
├── requirements.txt
├── CHANGELOG.md
└── README.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
```

## Requirements

See `requirements.txt` for pinned dependencies. All examples are tested against
the versions listed there. Check `CHANGELOG.md` for updates when newer versions
of model APIs or SDKs introduce breaking changes.

## Running Examples

Each chapter directory contains:
- Named Python files matching the `chNN_*.py` pattern used in the book
- An `exercises/` subdirectory with exercise solutions
- A `README.md` describing what each file demonstrates

Example:
```bash
cd chapters/ch05
python ch05_model_comparison.py
```

## Keeping Up to Date

This repository is updated monthly to track breaking changes in:
- Anthropic SDK (`anthropic`)
- Model API versions and capability changes
- Framework releases (LangGraph, AutoGen, Pydantic-AI)
- MCP SDK updates

Watch this repository or check `CHANGELOG.md` before running examples in production.

## Issues and Contributions

Found a broken example? Open an issue with:
1. The file path and line number
2. The error message
3. Your Python version and `pip list` output

Pull requests for bug fixes and updated dependency pins are welcome.

## License

Code examples are MIT licensed. See LICENSE file.
Book text and diagrams are copyright Jordan Caldwell, all rights reserved.
