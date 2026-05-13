"""
Chapter 20 — Coding Agents — Example 1
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch20_01_extract_python_symbols.py
"""
import os
from pathlib import Path
from typing import Optional
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())

def extract_python_symbols(source: str) -> list[dict]:
    """
    Parse a Python source file and extract top-level symbols
    (classes, functions, methods) with their signatures.
    Returns list of {type, name, signature, line} dicts.
    """
    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(bytes(source, "utf-8"))
    symbols = []
    lines = source.splitlines()

    def get_line(node) -> str:
        return lines[node.start_point[0]] if node.start_point[0] < len(lines) else ""

    def walk(node, class_name: Optional[str] = None):
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            params_node = node.child_by_field_name("parameters")
            return_node = node.child_by_field_name("return_type")

            name = name_node.text.decode() if name_node else "?"
            params = params_node.text.decode() if params_node else "()"
            returns = f" -> {return_node.text.decode()}" if return_node else ""

            sym_type = "method" if class_name else "function"
            qualified = f"{class_name}.{name}" if class_name else name
            symbols.append({
                "type": sym_type,
                "name": qualified,
                "signature": f"def {name}{params}{returns}:",
                "line": node.start_point[0] + 1,
            })

            # Don't recurse into nested functions for the map
            return

        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            cls_name = name_node.text.decode() if name_node else "?"
            symbols.append({
                "type": "class",
                "name": cls_name,
                "signature": get_line(node).strip(),
                "line": node.start_point[0] + 1,
            })
            for child in node.children:
                walk(child, class_name=cls_name)
            return

        for child in node.children:
            walk(child, class_name=class_name)

    walk(tree.root_node)
    return symbols

def build_repo_map(repo_root: str, max_files: int = 200) -> str:
    """
    Build a compact repository map showing file structure and
    top-level symbols for all Python files under repo_root.
    """
    repo_path = Path(repo_root)
    py_files = sorted(repo_path.rglob("*.py"))[:max_files]

    map_lines = [f"Repository map: {repo_root}", ""]

    for py_file in py_files:
        rel_path = py_file.relative_to(repo_path)
        # Skip vendored/generated code
        parts = rel_path.parts
        if any(p in parts for p in ("venv", ".venv", "node_modules", "__pycache__", "migrations")):
            continue

        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        symbols = extract_python_symbols(source)
        if not symbols:
            map_lines.append(f"{rel_path}")
            continue

        map_lines.append(f"{rel_path}")
        for sym in symbols:
            indent = "    " if sym["type"] == "method" else "  "
            map_lines.append(f"{indent}{sym['signature']}  # line {sym['line']}")
        map_lines.append("")

    return "\n".join(map_lines)

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = extract_python_symbols('example')
        print(result)
