#!/usr/bin/env python3
"""Render and save LangGraph pipeline visualization.

Usage:
    uv run -m log_ai_agent.ai_agent_v2.render_graph

Output:
    - ASCII graph printed to console
    - Mermaid diagram saved to ai_agent_v2/pipeline_graph.mmd
"""

import asyncio

# Add project root
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from log_ai_agent.ai_agent_v2.chains.graph_nodes import PipelineNodes
from log_ai_agent.ai_agent_v2.pipeline.langgraph_pipeline import build_analysis_graph


async def main():
    print("=" * 60)
    print("  Wavescan — Pipeline Graph Visualization")
    print("=" * 60)

    # Build nodes (no real LLM needed for graph structure)
    try:
        from langchain_core.language_models.fake import FakeListChatModel

        mock_llm = FakeListChatModel(responses=["mock"])
    except ImportError:
        from langchain_core.language_models import FakeListChatModel

        mock_llm = FakeListChatModel(responses=["mock"])

    nodes = PipelineNodes(llm=mock_llm, chroma_mgr=None, use_rag=False)
    graph = build_analysis_graph(nodes)

    # --- ASCII ---
    print("\n" + "=" * 60)
    print("  ASCII Graph")
    print("=" * 60)
    print(graph.get_graph().draw_ascii())

    # --- Mermaid ---
    mermaid = graph.get_graph().draw_mermaid()
    print("\n" + "=" * 60)
    print("  Mermaid Diagram")
    print("=" * 60)
    print(mermaid)

    # Save to file
    output_path = Path(__file__).parent / "pipeline_graph.mmd"
    output_path.write_text(mermaid, encoding="utf-8")
    print(f"\n[Saved] Mermaid diagram to: {output_path}")

    # --- Graph info ---
    g = graph.get_graph()
    print("\n" + "=" * 60)
    print("  Graph Summary")
    print("=" * 60)
    print(f"  Nodes: {len(g.nodes)}")
    for name, node in g.nodes.items():
        print(f"    - {name}")
    print(f"\n  Edges: {len(g.edges)}")
    for edge in g.edges:
        print(f"    {edge.source} → {edge.target}")

    print("\n" + "=" * 60)
    print("  To render Mermaid:")
    print("    1. https://mermaid.live — paste pipeline_graph.mmd")
    print("    2. VS Code: install 'Markdown Preview Mermaid' extension")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(0)
