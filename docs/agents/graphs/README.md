# Centralized LangGraph Architecture

## Overview

This directory contains centralized LangGraph definitions that are shared across agents. This architecture provides:

1. **Reusability**: Graphs can be composed and reused
2. **Maintainability**: Single source of truth for graph definitions
3. **State-based Routing**: Conditional edges for dynamic path selection
4. **Testability**: Graphs can be tested independently

## Structure

- `ingestion_graph.py`: Document ingestion workflow
- `flashcard_graph.py`: Flashcard generation workflow  
- `kg_graph.py`: Knowledge graph extraction workflow

## Usage Pattern

```python
from app.agents.graphs import build_ingestion_graph
from app.agents.service_tools import ServiceTools

# In agent __init__
service_tools = ServiceTools(db)
graph = build_ingestion_graph(service_tools, db)

# In _run_internal
initial_state = {
    "input_data": input_data,
    "service_tools": service_tools,
    "db": db,
    # ... other state fields
}
final_state = await graph.ainvoke(initial_state)
```

## Agent-to-Agent Communication

For agent-to-agent communication, use LangGraph conditional edges:

```python
# Route based on state, not intent
workflow.add_conditional_edges(
    "analyze",
    _should_call_agent,  # Returns "yes" or "no"
    {"yes": "call_agent", "no": "skip"}
)
```

This approach is:
- ✅ State-based (more reliable)
- ✅ Fast (no LLM overhead)
- ✅ Testable
- ✅ Part of workflow

