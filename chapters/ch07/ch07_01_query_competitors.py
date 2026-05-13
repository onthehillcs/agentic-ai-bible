"""
Chapter 7 — Memory — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch07_01_query_competitors.py
"""
# ch07_graph_memory.py (fragment)
# Tested against Neo4j 5.x, neo4j Python driver 5.x, as of April 2026.
# Requires: neo4j>=5.0

from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

def query_competitors(company_name: str) -> list[dict]:
    """Retrieve companies with a direct COMPETES_WITH relationship."""
    with driver.session() as session:
        result = session.run(
            "MATCH (c:Company {name: $name})-[:COMPETES_WITH]-(competitor:Company) "
            "RETURN competitor.name AS name, competitor.sector AS sector "
            "ORDER BY competitor.name",
            name=company_name,
        )
        return [dict(record) for record in result]

def query_shared_board_members(company_a: str, company_b: str) -> list[dict]:
    """Find executives who sit on the boards of both companies."""
    with driver.session() as session:
        result = session.run(
            "MATCH (a:Company {name: $a})<-[:BOARD_MEMBER_OF]-(p:Person)"
            "-[:BOARD_MEMBER_OF]->(b:Company {name: $b}) "
            "RETURN p.name AS person, p.title AS title",
            a=company_a, b=company_b,
        )
        return [dict(record) for record in result]

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = query_competitors('OpenAI')
        print(result)
