# Debug Mode Guide

This guide explains how to run and debug the MentraFlow backend in debug mode.

## Quick Start

### Option 1: VS Code Debugger (Recommended)

1. **Open the project in VS Code**
2. **Go to Run and Debug** (Ctrl+Shift+D / Cmd+Shift+D)
3. **Select "Python: FastAPI (Debug Mode)"** from the dropdown
4. **Press F5** or click the green play button

This will:
- Start the server with auto-reload enabled
- Enable debug logging
- Allow you to set breakpoints in your code
- Show detailed error tracebacks

### Option 2: Command Line with Debug Mode

```bash
# Using Makefile
make run-debug

# Or directly with uvicorn
DEBUG=true uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

### Option 3: Environment Variable

Add to your `.env` file:
```bash
DEBUG=true
```

Then run normally:
```bash
make run
```

## Debug Features

When `DEBUG=true`, the following features are enabled:

### 1. Verbose Logging
- **Log Level:** Changed from INFO to DEBUG
- **SQL Queries:** SQLAlchemy queries are logged
- **Request/Response:** Detailed request and response logging
- **Agent Execution:** Step-by-step agent execution logs

### 2. FastAPI Debug Mode
- **Better Error Pages:** Detailed error tracebacks in browser
- **Request Validation:** More detailed validation error messages
- **OpenAPI Docs:** Enhanced Swagger UI with debug info

### 3. Breakpoints
- Set breakpoints in VS Code by clicking left of line numbers
- Execution will pause at breakpoints
- Inspect variables, call stack, and execute code in debug console

## VS Code Debug Configurations

Three debug configurations are available:

### 1. Python: FastAPI (Debug Mode)
- **Best for:** General development and debugging
- **Features:** Auto-reload, debug logging, breakpoints
- **Use when:** You want to debug while developing

### 2. Python: FastAPI (No Reload)
- **Best for:** Debugging without auto-reload interference
- **Features:** Debug logging, breakpoints, no auto-reload
- **Use when:** Auto-reload is causing issues or you need stable debugging

### 3. Python: FastAPI (Current File)
- **Best for:** Running/debugging individual Python files
- **Features:** Run any Python file with debugger
- **Use when:** Testing scripts or utilities

## Setting Breakpoints

1. **Open any Python file** (e.g., `app/main.py`, `app/api/v1/endpoints/documents.py`)
2. **Click left of the line number** where you want to pause
3. **Red dot appears** = breakpoint set
4. **Run in debug mode** - execution will pause at breakpoint

### Breakpoint Types

- **Regular Breakpoint:** Always pauses
- **Conditional Breakpoint:** Right-click → "Edit Breakpoint" → Add condition
- **Logpoint:** Logs message without pausing (useful for production debugging)

## Debug Console

While paused at a breakpoint, you can:

- **Inspect Variables:** Hover over variables or check "Variables" panel
- **Evaluate Expressions:** Use Debug Console to run Python code
- **Step Through Code:**
  - **F10:** Step Over (next line)
  - **F11:** Step Into (enter function)
  - **Shift+F11:** Step Out (exit function)
  - **F5:** Continue (resume execution)

## Common Debug Scenarios

### Debug API Endpoint

1. Open the endpoint file (e.g., `app/api/v1/endpoints/documents.py`)
2. Set breakpoint in the endpoint function
3. Start debugger
4. Make API request (via curl, Postman, or frontend)
5. Execution pauses at breakpoint
6. Inspect `request` object, `db` session, etc.

### Debug Agent Execution

1. Open agent file (e.g., `app/agents/ingestion_agent.py`)
2. Set breakpoint in `_run_internal()` method
3. Start debugger
4. Trigger agent via API endpoint
5. Step through agent execution

### Debug Database Queries

1. Enable SQL logging (already enabled in debug mode)
2. Check console for SQL queries
3. Set breakpoint after query execution
4. Inspect query results

### Debug LangGraph Workflow

1. Open graph file (e.g., `app/agents/graphs/ingestion_graph.py`)
2. Set breakpoint in graph node function
3. Start debugger
4. Trigger agent - execution pauses at graph node
5. Inspect state dictionary

## Troubleshooting

### Debugger Not Starting

- **Check Python interpreter:** Ensure VS Code is using correct Python (`.venv/bin/python`)
- **Install debugpy:** `pip install debugpy` (usually included in requirements)
- **Check launch.json:** Verify configuration exists in `.vscode/launch.json`

### Breakpoints Not Hitting

- **Verify debug mode:** Ensure `DEBUG=true` in `.env` or launch config
- **Check file path:** Breakpoints only work in files that are actually executed
- **Restart debugger:** Sometimes need to restart debug session

### Auto-reload Interfering

- Use "Python: FastAPI (No Reload)" configuration
- Or disable auto-reload in launch.json: remove `--reload` from args

### Logs Too Verbose

- Adjust log level in `app/main.py`:
  ```python
  logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
  ```

## Environment Variables

Add to `.env` for debug mode:

```bash
# Enable debug mode
DEBUG=true

# Optional: More verbose SQL logging
SQLALCHEMY_ECHO=true  # (if you add this to config)
```

## Production Warning

⚠️ **Never enable DEBUG mode in production!**

- Exposes detailed error information
- Increases log volume significantly
- May impact performance
- Security risk (error details leak)

Always set `DEBUG=false` in production environments.

## Additional Resources

- [VS Code Python Debugging](https://code.visualstudio.com/docs/python/debugging)
- [FastAPI Debugging](https://fastapi.tiangolo.com/tutorial/debugging/)
- [Uvicorn Logging](https://www.uvicorn.org/settings/#logging)

