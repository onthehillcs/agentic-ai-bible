"""
Chapter 17 — Cost, Latency, and Performance — Example 3
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch17_03_get_encoder.py
"""
# Tested with Python 3.11, tiktoken==0.6.0, openai==1.14.0
# Token budget management for agent pipeline cost control

import tiktoken
from typing import Optional

# Cache the encoder - initializing it for every call is expensive
_encoders: dict[str, tiktoken.Encoding] = {}

def get_encoder(model: str) -> tiktoken.Encoding:
    """Get the tokenizer for a model, with caching."""
    if model not in _encoders:
        try:
            _encoders[model] = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fall back to cl100k_base for unknown models
            _encoders[model] = tiktoken.get_encoding('cl100k_base')
    return _encoders[model]


def count_tokens(text: str, model: str = 'gpt-4o') -> int:
    """Count the number of tokens in a text string."""
    enc = get_encoder(model)
    return len(enc.encode(text))


def count_messages_tokens(messages: list[dict], model: str = 'gpt-4o') -> int:
    """Count tokens for a messages array including format overhead."""
    enc = get_encoder(model)
    total = 0
    # Each message has 3 overhead tokens (role + content + separator)
    for msg in messages:
        total += 3
        total += len(enc.encode(msg.get('content') or ''))
        total += len(enc.encode(msg.get('role', '')))
    total += 3  # Reply priming
    return total


def truncate_to_token_budget(
    text: str,
    max_tokens: int,
    model: str = 'gpt-4o',
    truncation_note: str = '\n[... truncated to fit token budget ...]',
) -> str:
    """Truncate text to fit within a token budget.
    
    Truncates from the end, preserving the beginning of the document
    (which typically contains the most relevant information for most
    document types).
    """
    enc = get_encoder(model)
    tokens = enc.encode(text)
    
    if len(tokens) <= max_tokens:
        return text
    
    # Reserve tokens for the truncation note
    note_tokens = len(enc.encode(truncation_note))
    keep_tokens = max_tokens - note_tokens
    
    truncated = enc.decode(tokens[:keep_tokens])
    return truncated + truncation_note


class PipelineTokenBudget:
    """Tracks token consumption across an agent pipeline run and enforces limits."""
    
    def __init__(self, max_input_tokens: int = 100_000, max_output_tokens: int = 10_000):
        self.max_input = max_input_tokens
        self.max_output = max_output_tokens
        self.used_input = 0
        self.used_output = 0
        self.step_counts: list[dict] = []
    
    def record_call(self, step_name: str, input_tokens: int, output_tokens: int):
        """Record tokens used by an LLM call."""
        self.used_input += input_tokens
        self.used_output += output_tokens
        self.step_counts.append({
            'step': step_name,
            'input': input_tokens,
            'output': output_tokens,
        })
    
    def remaining_input_budget(self) -> int:
        return max(0, self.max_input - self.used_input)
    
    def remaining_output_budget(self) -> int:
        return max(0, self.max_output - self.used_output)
    
    def is_input_budget_exhausted(self) -> bool:
        return self.used_input >= self.max_input
    
    def summary(self) -> dict:
        return {
            'total_input_tokens': self.used_input,
            'total_output_tokens': self.used_output,
            'input_budget_used_pct': 100 * self.used_input / self.max_input,
            'output_budget_used_pct': 100 * self.used_output / self.max_output,
            'step_breakdown': self.step_counts,
        }

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = get_encoder('example')
        print(result)
