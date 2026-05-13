"""
Chapter 7 — Memory — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch07_02_retrieve_episodic.py
"""
# ch07_memory_agent.py
# Tested against Claude Sonnet 4.6 (claude-sonnet-4-6-20250514),
# Anthropic SDK 0.49.0, ChromaDB 0.6.x, as of April 2026.
# Requires: anthropic>=0.49, chromadb>=0.6, tavily-python>=0.5

import json
import uuid
import anthropic
import chromadb
from tavily import TavilyClient
from datetime import datetime

client = anthropic.Anthropic()
tavily = TavilyClient()
chroma = chromadb.PersistentClient(path="/tmp/agent_memory")  # persistent storage

episodic_store = chroma.get_or_create_collection("episodic")
semantic_store = chroma.get_or_create_collection("semantic")


def retrieve_episodic(query: str, user_id: str, k: int = 3) -> list[str]:
    results = episodic_store.query(
        query_texts=[query],
        n_results=k,
        where={"user_id": user_id},  # metadata filter: only this user's memories
    )
    return results["documents"][0] if results["documents"] else []


def save_episodic(summary: str, user_id: str, session_id: str) -> None:
    episodic_store.add(
        documents=[summary],
        metadatas=[{"user_id": user_id, "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "embedding_model": "chroma-default-v1"}],  # track embedding model version
        ids=[session_id],
    )


def retrieve_semantic(query: str, k: int = 4) -> list[str]:
    results = semantic_store.query(query_texts=[query], n_results=k)
    return results["documents"][0] if results["documents"] else []


def summarize_session(messages: list[dict]) -> str:  # session summarization
    summary_prompt = (
        "Review the following conversation and extract: "
        "(1) the main research questions asked, "
        "(2) key facts or conclusions reached, "
        "(3) any user preferences expressed, "
        "(4) open threads that were not fully resolved. "
        "Be specific. Do not summarize vaguely. Output plain text, max 300 words."
    )
    response = client.messages.create(
        model="claude-haiku-3-5-20241022",  # cheaper model for summarization
        max_tokens=512,
        system=summary_prompt,
        messages=[{"role": "user", "content": json.dumps(messages)}],
    )
    return response.content[0].text


SEARCH_TOOL = {
    "name": "search_news",
    "description": (
        "Search recent news articles. Use for current events, recent company news, "
        "or any fact that may have changed in the past 90 days. "
        "For stable factual questions, check the knowledge context injected at the start first."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "days_back": {"type": "integer"},
        },
        "required": ["query", "days_back"],
    },
}


def run_research_session(user_message: str, user_id: str) -> str:
    session_id = str(uuid.uuid4())

    # Retrieve and inject relevant memories before the session starts
    past_sessions = retrieve_episodic(user_message, user_id)
    knowledge_chunks = retrieve_semantic(user_message)

    memory_context = ""
    if past_sessions:
        memory_context += "\n\n--- PAST SESSIONS (may be outdated; verify with user if uncertain) ---\n"
        memory_context += "\n".join(past_sessions)
    if knowledge_chunks:
        memory_context += "\n\n--- RELEVANT KNOWLEDGE ---\n"
        memory_context += "\n".join(knowledge_chunks)

    system = (
        "You are a financial research assistant. "
        "Help the analyst research companies and markets. "
        + memory_context
    )

    messages = [{"role": "user", "content": user_message}]
    all_messages = list(messages)

    for _ in range(10):
        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=2048,
            system=system,
            tools=[SEARCH_TOOL],
            messages=messages,
        )
        if response.stop_reason == "end_turn":
            final_answer = next((b.text for b in response.content if hasattr(b, "text")), "")
            all_messages.append({"role": "assistant", "content": final_answer})
            # Summarize and save the session to episodic memory before returning
            summary = summarize_session(all_messages)
            save_episodic(summary, user_id, session_id)
            return final_answer

        messages.append({"role": "assistant", "content": response.content})
        all_messages.append({"role": "assistant", "content": str(response.content)})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                articles = tavily.search(
                    query=block.input["query"],
                    max_results=5,
                    days=block.input["days_back"],
                )["results"]
                result_text = json.dumps(articles)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })
                all_messages.append({"role": "tool", "content": result_text})
        messages.append({"role": "user", "content": tool_results})

    return "Session exceeded iteration budget."

if __name__ == '__main__':
    result = retrieve_episodic('example task query')
    print(result)
