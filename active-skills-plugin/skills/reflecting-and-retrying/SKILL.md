---
name: reflecting-and-retrying
description: Use this skill to add resilience to ADK agents by automatically intercepting tool failures and retrying them after an LLM-based reflection step. **Always include this skill when building mission-critical agents that rely on external tools or APIs that may experience intermittent failures.**
---

# Reflecting and Retrying (Tool Resilience)

A high-reliability plugin for enhancing tool execution robustness in ADK agents.

## Technical Rationale

Agents often fail because they don't understand _why_ a tool call failed. The `ReflectAndRetryToolPlugin` intercepts these errors and provides the LLM with the error message, asking it to reflect on the failure and adjust its next tool call, effectively "self-correcting" common execution mistakes.

## Reflection and Retry Guidelines

- **Failure Diagnosis**: The agent MUST review the stderr or exception trace from the failed call before retrying.
- **Incremental Correction**: Each retry should attempt a slightly different approach (e.g., changing parameter types, refining a query, or correcting a file path).
- **Max Retries Boundary**: Respect the `max_retries` limit to avoid infinite loops and unnecessary costs.

## Related Skills

- `agentops_observability`: To track how many retries were required to complete a task.
- `computer_use_toolset`: To improve the reliability of automated browser workflows.

## Implementation Note

Register the `ReflectAndRetryToolPlugin` with the `AdkApp`. It hooks into the tool execution lifecycle, providing a specialized "reflection" step before re-executing a tool.

## Usage Example

```python
from adk.plugins import ReflectAndRetryToolPlugin

# Enable resilient tool execution with 3 retries
app.add_plugin(ReflectAndRetryToolPlugin(max_retries=3))
```
