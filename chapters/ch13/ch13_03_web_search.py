"""
Chapter 13 — Long-Running and Async Agents — Example 3
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch13_03_web_search.py
"""
# Tested with Python 3.11, openai==1.14.0, requests==2.31.0
# Multi-day research agent with checkpoint/resume
# Requires: CheckpointManager from earlier in this chapter

import uuid
import time
import json
import hashlib
from dataclasses import dataclass
from typing import Optional
from openai import OpenAI
from pathlib import Path

client = OpenAI()

# Simulated tool implementations (replace with real implementations)
def web_search(query: str, max_results: int = 10) -> list[dict]:
    """Search the web and return structured results."""
    # In production: call Bing Search API, SerpAPI, or Brave Search
    return [{"title": f"Result for {query}", "url": f"https://example.com/{i}",
             "snippet": f"Content about {query}"} for i in range(max_results)]

def fetch_document(url: str) -> str:
    """Fetch and parse a document from a URL."""
    # In production: use requests + newspaper3k or similar
    return f"Document content from {url}"

def cache_key(func_name: str, **kwargs) -> str:
    """Generate a deterministic cache key for tool calls."""
    payload = json.dumps({"func": func_name, **kwargs}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class ResearchPlan:
    run_id: str
    company: str
    competitors: list[str]
    search_queries: list[str]
    cost_limit_usd: float = 10.0


class MultiDayResearchAgent:
    """A research agent that checkpoints between stages and can be resumed
    after interruption, machine restart, or rate-limit backoff.
    """
    
    STAGES = [
        'plan',
        'search',
        'fetch_documents',
        'analyze_sources',
        'synthesize',
        'format_report'
    ]
    
    def __init__(self, checkpoint_mgr: CheckpointManager):
        self.cp = checkpoint_mgr
        self.tool_cache: dict[str, Any] = {}
    
    def run(self, plan: ResearchPlan, resume: bool = True) -> dict:
        """Execute the research pipeline, resuming from the last checkpoint
        if resume=True and a prior run exists for this run_id.
        """
        print(f"[{plan.run_id}] Starting research for {plan.company}")
        
        # Load existing checkpoints to determine where to resume
        existing = {c.stage_name: c for c in self.cp.load_all(plan.run_id)}
        completed_stages = {
            name for name, cp in existing.items() if cp.status == 'complete'
        }
        
        if completed_stages and resume:
            print(f"[{plan.run_id}] Resuming from after: {max(completed_stages, key=lambda s: self.STAGES.index(s))}")
        
        results = {
            name: existing[name].outputs
            for name in completed_stages
            if name in existing
        }
        
        stage_methods = {
            'plan': self._stage_plan,
            'search': self._stage_search,
            'fetch_documents': self._stage_fetch,
            'analyze_sources': self._stage_analyze,
            'synthesize': self._stage_synthesize,
            'format_report': self._stage_format,
        }
        
        for idx, stage_name in enumerate(self.STAGES):
            if stage_name in completed_stages:
                print(f"[{plan.run_id}] Skipping completed stage: {stage_name}")
                continue
            
            # Cost gate: check total spend before each stage
            total_cost = sum(
                existing[s].cost_usd for s in completed_stages if s in existing
            )
            if total_cost >= plan.cost_limit_usd:
                raise RuntimeError(
                    f"Cost limit ${plan.cost_limit_usd} reached at stage {stage_name}. "
                    f"Total spent: ${total_cost:.4f}"
                )
            
            print(f"[{plan.run_id}] Executing stage {idx+1}/{len(self.STAGES)}: {stage_name}")
            
            # Start checkpoint
            cp = Checkpoint(
                run_id=plan.run_id,
                stage_name=stage_name,
                stage_index=idx,
                inputs={'plan': vars(plan), 'prior_results': list(results.keys())},
                outputs={},
                token_count=0,
                cost_usd=0.0,
                wall_time_start=time.time(),
                wall_time_end=None,
                status='in_progress'
            )
            self.cp.save(cp)
            
            try:
                # Execute stage
                stage_outputs = stage_methods[stage_name](plan, results)
                
                # Save successful checkpoint
                cp.outputs = stage_outputs
                cp.cost_usd = stage_outputs.pop('_cost_usd', 0.0)
                cp.token_count = stage_outputs.pop('_token_count', 0)
                cp.wall_time_end = time.time()
                cp.status = 'complete'
                self.cp.save(cp)
                
                results[stage_name] = stage_outputs
                print(f"[{plan.run_id}] Stage {stage_name} complete. Cost: ${cp.cost_usd:.4f}")
            
            except RateLimitError as e:
                cp.status = 'failed'
                cp.wall_time_end = time.time()
                self.cp.save(cp)
                retry_after = getattr(e, 'retry_after', 3600)
                print(f"[{plan.run_id}] Rate limited on stage {stage_name}. Retry after {retry_after}s")
                # In production: enqueue a delayed retry via Celery
                raise
            
            except Exception as e:
                cp.status = 'failed'
                cp.wall_time_end = time.time()
                self.cp.save(cp)
                raise
        
        return results.get('format_report', {})
    
    def _stage_plan(self, plan: ResearchPlan, prior: dict) -> dict:
        """Use the LLM to expand the research plan into specific search queries."""
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": f"""Generate 15 specific search queries to research competitive
                landscape for {plan.company} vs {', '.join(plan.competitors)}.
                Return as JSON array of strings."""
            }],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        cost = (response.usage.prompt_tokens * 0.000005 +
                response.usage.completion_tokens * 0.000015)
        return {
            'queries': data.get('queries', plan.search_queries),
            '_cost_usd': cost,
            '_token_count': response.usage.total_tokens
        }
    
    def _stage_search(self, plan: ResearchPlan, prior: dict) -> dict:
        """Execute all search queries and collect results."""
        queries = prior.get('plan', {}).get('queries', plan.search_queries)
        all_results = []
        
        for query in queries:
            key = cache_key('web_search', query=query)
            if key not in self.tool_cache:
                self.tool_cache[key] = web_search(query)
            all_results.extend(self.tool_cache[key])
        
        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            if r['url'] not in seen_urls:
                seen_urls.add(r['url'])
                unique_results.append(r)
        
        return {
            'results': unique_results[:50],  # Cap at 50 unique sources
            '_cost_usd': 0.0,  # Web search cost tracked separately
            '_token_count': 0
        }
    
    def _stage_fetch(self, plan: ResearchPlan, prior: dict) -> dict:
        """Fetch and extract text from top search result URLs."""
        results = prior.get('search', {}).get('results', [])
        documents = []
        
        for result in results[:20]:  # Fetch top 20 documents
            key = cache_key('fetch_document', url=result['url'])
            if key not in self.tool_cache:
                self.tool_cache[key] = fetch_document(result['url'])
            documents.append({
                'url': result['url'],
                'title': result['title'],
                'content': self.tool_cache[key][:2000]  # Truncate to 2k chars
            })
        
        return {'documents': documents, '_cost_usd': 0.0, '_token_count': 0}
    
    def _stage_analyze(self, plan: ResearchPlan, prior: dict) -> dict:
        """Analyze each document with the LLM to extract competitive intelligence."""
        documents = prior.get('fetch_documents', {}).get('documents', [])
        analyses = []
        total_cost = 0.0
        total_tokens = 0
        
        for doc in documents:
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Use cheaper model for per-document analysis
                messages=[{
                    "role": "user",
                    "content": f"""Extract competitive intelligence from this document
                    about {plan.company} and its competitors {plan.competitors}.
                    Return JSON with keys: key_facts, competitive_implications, credibility_score (1-5).
                    
                    Document: {doc['content']}"""
                }],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            cost = (response.usage.prompt_tokens * 0.00000015 +
                    response.usage.completion_tokens * 0.0000006)
            total_cost += cost
            total_tokens += response.usage.total_tokens
            
            try:
                analysis = json.loads(response.choices[0].message.content)
                analyses.append({'url': doc['url'], **analysis})
            except json.JSONDecodeError:
                analyses.append({'url': doc['url'], 'key_facts': [], 'error': 'parse_failed'})
        
        return {'analyses': analyses, '_cost_usd': total_cost, '_token_count': total_tokens}
    
    def _stage_synthesize(self, plan: ResearchPlan, prior: dict) -> dict:
        """Synthesize all analyses into a coherent competitive intelligence brief."""
        analyses = prior.get('analyze_sources', {}).get('analyses', [])
        high_quality = [a for a in analyses if a.get('credibility_score', 0) >= 3]
        
        synthesis_prompt = f"""You are writing a competitive intelligence brief for {plan.company}.
        Based on {len(high_quality)} analyzed sources, synthesize the key competitive dynamics,
        threats, and opportunities. Be specific and cite sources.
        
        Analyses:\n{json.dumps(high_quality[:15], indent=2)}"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": synthesis_prompt}],
            temperature=0.3,
        )
        
        cost = (response.usage.prompt_tokens * 0.000005 +
                response.usage.completion_tokens * 0.000015)
        
        return {
            'synthesis': response.choices[0].message.content,
            '_cost_usd': cost,
            '_token_count': response.usage.total_tokens
        }
    
    def _stage_format(self, plan: ResearchPlan, prior: dict) -> dict:
        """Format the synthesis into a polished report document."""
        synthesis = prior.get('synthesize', {}).get('synthesis', '')
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": f"""Format this competitive intelligence synthesis as a
                professional report with Executive Summary, Key Findings, Competitive
                Threats, Strategic Opportunities, and Methodology sections.
                Use markdown formatting.
                
                Synthesis:\n{synthesis}"""
            }],
            temperature=0.2,
        )
        
        cost = (response.usage.prompt_tokens * 0.000005 +
                response.usage.completion_tokens * 0.000015)
        
        return {
            'report': response.choices[0].message.content,
            'generated_at': time.time(),
            '_cost_usd': cost,
            '_token_count': response.usage.total_tokens
        }


# Usage: start or resume a research run
if __name__ == '__main__':
    cp_mgr = CheckpointManager("/tmp/research_checkpoints.db")
    agent = MultiDayResearchAgent(cp_mgr)
    
    # This run_id can be stored externally and used to resume
    run_id = "research-acme-2024-q1"  # Deterministic ID for resumability
    
    plan = ResearchPlan(
        run_id=run_id,
        company="Acme Corp",
        competitors=["Widget Co", "Gadget Inc", "Thingamajig Ltd"],
        search_queries=["Acme Corp news 2024", "Widget Co product launch"],
        cost_limit_usd=8.0
    )
    
    report = agent.run(plan, resume=True)
    print("Report generated:")
    print(report.get('report', 'No report generated'))
