"""
Chapter 11 — Multi-Agent Systems — Example 9
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch11_09__11_9_agent_communication_protocols.py
"""

_TEXT = """
These tests do not call the live API, which means they run in under a second and are appropriate for the standard CI pre-merge gate. The mock response builder replicates the structure that the real `anthropic` client returns, including the `usage` object, so that the metrics logic is tested alongside the control flow. The degradation tests verify the fault tolerance policy by name: research failure should produce a complete run with empty precedents, while extraction and writing failures should abort. If someone changes the fault tolerance policy in the implementation without updating the tests, the tests will catch the discrepancy.

## 11.9 Agent Communication Protocols

A multi-agent system running entirely within a single Python process can pass rich Python objects between agents without any serialization. Once agents run on separate machines, communicate over a message queue, or are implemented in different languages, inter-agent messages must be serialized to a wire format, transmitted, and deserialized on the receiving end. The choices made at this boundary have lasting consequences for the system's reliability, debuggability, and ability to evolve.

The wire format choice is the first decision. JSON is the most common choice for agent-to-agent communication because it is human-readable, broadly supported, and easy to inspect in logs and debugging sessions. Its weakness is that it has no native type for dates, binary data, or integers larger than 53 bits, and it provides no built-in schema enforcement. Protocol Buffers and MessagePack are more compact and faster to serialize, but they require a schema definition file and a code generation step that adds friction to rapid iteration. For most agent systems in 2026, JSON with Pydantic validation at the boundary is the right balance between readability, type safety, and implementation speed.

Message versioning is the second decision, and the one teams most frequently skip. When agent A sends a message to agent B and both agents are deployed independently, a schema change to the message type can break the system if A and B are not updated simultaneously. The solution is to include a version field in every inter-agent message and to write receiving agents to accept both the current and previous versions of each message type for at least one release cycle. This gives the team the ability to deploy agent A with the new schema and then deploy agent B, without requiring a coordinated lockstep deployment.
"""

if __name__ == '__main__':
    print(_TEXT)
