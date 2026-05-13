"""
Chapter 7 — Memory — Example 3
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch07_03__doc_id.py
"""
# requires ANTHROPIC_API_KEY
# pip install chromadb anthropic
import anthropic
import chromadb
import hashlib, json, datetime

client   = anthropic.Anthropic()
chroma   = chromadb.PersistentClient(path="/tmp/research_memory")
collection = chroma.get_or_create_collection("research_sessions")

SONNET = "claude-sonnet-4-5"

def _doc_id(question: str) -> str:
    return hashlib.sha256(question.encode()).hexdigest()[:16]

def recall_prior(question: str, n_results: int = 3) -> list:
    # Return summaries of past sessions semantically similar to question.
    results = collection.query(query_texts=[question], n_results=n_results)
    return results["documents"][0] if results["documents"] else []

def store_session(question: str, answer: str, sources: list) -> None:
    # Persist a completed research session to ChromaDB.
    doc = json.dumps({"question": question, "answer": answer, "sources": sources,
                      "timestamp": datetime.datetime.utcnow().isoformat()})
    collection.upsert(ids=[_doc_id(question)], documents=[doc])

def run_research_with_memory(question: str) -> str:
    # Check episodic memory before touching the network
    prior = recall_prior(question)
    memory_context = ""
    if prior:
        memory_context = (
            "You have researched related questions before. "
            "Relevant prior findings:\n" +
            "\n".join(f"[prior] {p}" for p in prior) + "\n\n"
        )

    response = client.messages.create(
        model=SONNET,
        max_tokens=2048,
        system=(
            "You are a research assistant. "
            + memory_context +
            "Answer the user's question. If prior findings already cover it, "
            "say so and extend them rather than repeating the same searches."
        ),
        messages=[{"role": "user", "content": question}],
    )
    answer = response.content[0].text
    # Persist this session for future recall
    store_session(question, answer, sources=[])
    return answer

if __name__ == "__main__":
    q1 = "What caused the 2023 banking crisis?"
    print(run_research_with_memory(q1))   # cold — no prior memory
    print("---")
    q2 = "How did the SVB collapse relate to interest rate policy?"
    print(run_research_with_memory(q2))   # warm — should recall the first session
