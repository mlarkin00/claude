# Vertex AI Prompt Optimizer API Reference

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [SDK Installation](#sdk-installation)
4. [Client Initialization](#client-initialization)
5. [Zero-Shot Optimization](#zero-shot-optimization)
6. [OptimizeConfig Parameters](#optimizeconfig-parameters)
7. [Response Structure](#response-structure)
8. [Steering Hints Strategy](#steering-hints-strategy)
9. [Supported Regions](#supported-regions)
10. [Quotas and Limits](#quotas-and-limits)
11. [Error Reference](#error-reference)

---

## Overview

The Vertex AI Prompt Optimizer uses an LLM-based meta-prompt pipeline to rewrite a given prompt to be clearer, more specific, and better aligned with the model's strengths. Zero-shot mode requires no labeled examples — only the prompt (and optional task context).

---

## Authentication

```bash
gcloud auth application-default login
# Required role: roles/aiplatform.user
```

Service account alternative:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

---

## SDK Installation

```bash
pip install "google-cloud-aiplatform>=1.87.0"
```

---

## Client Initialization

```python
import vertexai

client = vertexai.Client(project="your-project-id", location="us-central1")
```

---

## Zero-Shot Optimization

```python
from vertexai.types import OptimizeConfig, OptimizeTarget

response = client.prompt_optimizer.optimize_prompt(
    prompt="Tell me about black holes in a way a kid can understand.",
    config=OptimizeConfig(
        optimization_target=OptimizeTarget.OPTIMIZATION_TARGET_DEFAULT
    )
)

print(response.parsed_response.suggested_prompt)
```

### With Steering Hints

Steering hints are injected into the prompt body before the API call:

```python
prompt_with_hints = (
    "Tell me about black holes in a way a kid can understand."
    "\n\n[Optimization constraints: Avoid jargon; Keep under 100 words]"
)

response = client.prompt_optimizer.optimize_prompt(
    prompt=prompt_with_hints,
    config=OptimizeConfig(
        optimization_target=OptimizeTarget.OPTIMIZATION_TARGET_DEFAULT
    )
)
```

---

## OptimizeConfig Parameters

| Parameter             | Type             | Description                                                                |
| --------------------- | ---------------- | -------------------------------------------------------------------------- |
| `optimization_target` | `OptimizeTarget` | Optimization objective. Use `OPTIMIZATION_TARGET_DEFAULT` for general use. |

### OptimizeTarget Values

| Value                         | Description                  |
| ----------------------------- | ---------------------------- |
| `OPTIMIZATION_TARGET_DEFAULT` | General-purpose optimization |
| `OPTIMIZATION_TARGET_QUALITY` | Maximize output quality      |
| `OPTIMIZATION_TARGET_SAFETY`  | Reduce harmful output risk   |

---

## Response Structure

```python
response.parsed_response.suggested_prompt  # str — the optimized prompt
```

Full response object fields (where available):

```json
{
  "suggested_prompt": "string",
  "explanation": "string (optional)",
  "confidence_score": "float (optional)"
}
```

---

## Steering Hints Strategy

Steering hints are not a native API parameter — they are injected as structured context in the prompt body using the `[Optimization constraints: ...]` pattern. This tells the optimizer what to optimize toward or avoid.

**Effective hint patterns:**

| Goal           | Example Hint                      |
| -------------- | --------------------------------- |
| Length control | `Keep under 100 words`            |
| Tone           | `Use formal academic tone`        |
| Audience       | `Target audience: 8-year-olds`    |
| Preservation   | `Do not change the XML structure` |
| Avoidance      | `Avoid technical jargon`          |
| Format         | `Output as a numbered list`       |

**Accumulation across iterations:** All prior hints carry forward. Never discard earlier steering — later hints refine, not replace, earlier constraints.

---

## Supported Regions

Primary: `us-central1`

Additional regions where available: `us-east4`, `europe-west4`, `asia-northeast1`

---

## Quotas and Limits

- Prompt length: check current Vertex AI quotas via Cloud Console
- Requests per minute: varies by project tier
- Quota errors return HTTP 429 / `RESOURCE_EXHAUSTED`

---

## Error Reference

| Error Code                 | Cause                               | Resolution                                           |
| -------------------------- | ----------------------------------- | ---------------------------------------------------- |
| `PERMISSION_DENIED` / 403  | Missing IAM role or API not enabled | Enable Vertex AI API; grant `roles/aiplatform.user`  |
| `RESOURCE_EXHAUSTED` / 429 | Quota exceeded                      | Wait and retry; request quota increase               |
| `INVALID_ARGUMENT` / 400   | Malformed prompt or config          | Check prompt for null bytes or disallowed characters |
| `UNAUTHENTICATED` / 401    | No valid credentials                | Run `gcloud auth application-default login`          |
| `NOT_FOUND` / 404          | Wrong project or region             | Verify project ID and location                       |
