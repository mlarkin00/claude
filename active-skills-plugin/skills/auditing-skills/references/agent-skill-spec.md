# **Agent Skills Specification and Development (v1.1)**

The transition from monolithic system prompts to modular, discoverable expertise marks a fundamental pivot in the maturation of autonomous agentic systems. Historically, artificial intelligence models were constrained by the structural limitations of "mega-prompts," where every operational policy, safety guideline, and domain-specific procedure was injected into the context window at the beginning of every session. This architectural bottleneck inevitably led to ballooning operational costs, instruction drift, and the degradation of performance as critical directives were buried within excessive context. The Agent Skills specification, as established through the industry-standard framework at agentskills.io, offers a formal solution by packaging procedural knowledge, executable scripts, and static resources into portable, filesystem-based modules that agents can discover and load dynamically. By utilizing a three-tier loading model known as progressive disclosure, the specification ensures that agents remain high-signal, high-efficiency collaborators capable of executing complex, multi-step workflows without overwhelming the underlying model’s attention mechanisms or the user’s token budget.

## **The Formal Specification: Directory Hierarchy and Metadata Standards**

The Agent Skills specification defines a skill as a self-contained directory containing a primary definition file and optional subdirectories for supporting resources. This filesystem-based approach allows skills to be version-controlled, shared via standard Git workflows, and integrated across diverse platforms including command-line interfaces, integrated development environments (IDEs), local development tools, and various open-source agent frameworks. The absolute requirement for any valid skill is the existence of a SKILL.md file located at the root of the directory.

### **Structural Anatomy and Naming Conventions**

The parent directory of a skill must adhere to strict naming conventions to ensure discoverability across different operating systems and agent implementations. The directory name serves as the primary identifier and must consist solely of lowercase alphanumeric characters and hyphens. The specification prohibits the use of underscores, spaces, or uppercase letters, as these can lead to silent loading failures on case-sensitive filesystems or within certain agent runtimes.

| Directory Component | Requirement | Status    | Primary Technical Function                                               |
| :------------------ | :---------- | :-------- | :----------------------------------------------------------------------- |
| skill-name/         | Required    | Mandatory | Root directory; name must exactly match the name field in frontmatter.   |
| SKILL.md            | Required    | Mandatory | Entry point; contains YAML frontmatter and core Markdown instructions.   |
| scripts/            | Optional    | Supported | Executable code (Bash, Python, JS) for deterministic operations.         |
| references/         | Optional    | Supported | High-density documentation and domain-specific knowledge bases.          |
| assets/             | Optional    | Supported | Static resources, templates, schemas, diagrams, and image files.         |
| templates/          | Optional    | Supported | Starter code or scaffolds that the agent modifies and builds upon.       |
| evals/              | Recommended | Optional  | Standardized test queries and evaluation datasets for quality assurance. |

The internal organization of these subdirectories is purposefully flat. To minimize the cognitive load on the agent during file retrieval, the specification recommends that resources remain exactly one level deep from the SKILL.md file. While not a hard limit, deeply nested directory structures frequently introduce complexity in relative pathing that can confuse the agent’s autonomous reasoning during execution.

### **The SKILL.md Frontmatter Definition**

The SKILL.md file is the technical "brain" of the skill, bifurcated into two sections: the YAML frontmatter and the Markdown body content. The frontmatter acts as the Level 1 metadata layer, providing the necessary routing information for the agent to match user queries with the appropriate capability.

| Frontmatter Field | Requirement | Constraints                   | Technical Implications                                         |
| :---------------- | :---------- | :---------------------------- | :------------------------------------------------------------- |
| name              | Required    | 1-64 characters; kebab-case.  | Used as the slash command identifier (e.g., /deploy).          |
| description       | Required    | 1-1024 characters; non-empty. | The primary signal used for semantic discovery and routing.    |
| license           | Optional    | SPDX or file reference.       | Defines the legal usage and sharing boundaries.                |
| compatibility     | Optional    | 1-500 characters.             | Lists system packages (e.g., git, jq) or network requirements. |
| metadata          | Optional    | Arbitrary key-value map.      | Stores versioning, author info, or platform-specific tags.     |
| allowed-tools     | Optional    | Space-delimited string.       | Experimental field for pre-approving specific system tools.    |

The name field must match the directory name exactly; any discrepancy between the two will typically result in a discovery failure. For example, a skill intended to assist with web application testing should be housed in a folder named webapp-test and contain the field name: webapp-test. This consistency allows agent runtimes to map filesystem paths directly to internal command registries.

## **The Progressive Disclosure Paradigm: Token Efficiency and Execution Tiers**

The central innovation of the Agent Skills format is its tiered loading system, specifically engineered to manage the finite resource of the LLM context window. This architecture applies a "just-in-time" philosophy to knowledge injection, ensuring that an agent can have access to hundreds of skills without suffering from context exhaustion.

### **Level 1: Discovery Metadata**

At the initialization of an agent session, only the name and description of every installed skill are loaded into the system prompt. This metadata layer acts as a "menu" of capabilities. Because this metadata is always present in the context, it must remain highly concise. In a typical implementation, each skill consumes approximately 100 tokens at this stage.

### **Level 2: Core Instruction Body**

When an agent identifies a high-confidence match between a user's prompt and a skill's description, it triggers the loading of the full SKILL.md Markdown body. This second tier contains the procedural heart of the skill, including step-by-step workflows and "Gotchas" sections. The specification recommends that the SKILL.md body remain under 500 lines or 5,000 tokens. This limit ensures that the agent retains high attention toward the core instructions while maintaining sufficient room in the context window for task execution.

### **Level 3: Just-in-Time Resources**

High-density technical data, large code templates, and executable logic reside at the third level. These resources—located in scripts/, references/, and assets/—are never loaded into the context window until the agent explicitly chooses to read or execute them. For instance, a skill for database migrations might include several hundred megabytes of historical schema references; the agent will only read the specific schema relevant to the current migration task, thereby preserving tokens for the actual code generation.

## **Determining Content: The Creator's Methodology**

The efficacy of a skill depends on the creator's ability to distinguish between general knowledge and specialized procedural expertise. Effective skill creation is less about traditional prompt engineering and more about extracting the "non-obvious" facts and workflows that a general-purpose model would lack without specific guidance.

### **Grounding in Empirical Expertise**

The most robust skills are extracted from successful hands-on tasks rather than written in isolation. Developers are encouraged to complete a task manually with an agent first, carefully noting the specific steps that led to success and the errors that required manual correction. This "trace" of execution serves as the blueprint for the skill. If an agent repeatedly makes a specific mistake—such as forgetting to update a manifest file after a deployment—that mistake should be codified as a mandatory instruction or a "Gotcha".

### **Scoping the Utility: Coherence vs. Complexity**

Deciding what a skill should cover is analogous to deciding what a function should do in software engineering. A skill should encapsulate a coherent unit of work that composes well with other skills.

| Skill Scope    | Goal                                                         | Risk of Overscoping                                                       |
| :------------- | :----------------------------------------------------------- | :------------------------------------------------------------------------ |
| **Atomic**     | Handles one specific task (e.g., git-commit).               | Too many skills loading simultaneously, causing conflicting instructions. |
| **Balanced**   | Covers a complete workflow (e.g., webapp-test).              | Ideal; encapsulated and discoverable without excessive bloat.             |
| **Monolithic** | Tries to handle entire domains (e.g., cloud-infrastructure). | Hard to activate precisely; irrelevant context confuses the agent.        |

Creators should ask: "Would the agent get this wrong without this specific instruction?" If the answer is no, the content should be omitted to save tokens. If the agent handles the task well with its base knowledge, the skill adds no value and may actually degrade performance by over-constraining the model's reasoning.

## **Artifact Preparation: References, Assets, and Scripts**

The difference between a mediocre skill and a production-grade asset lies in the quality of the supporting artifacts. These files must be engineered specifically for consumption by an LLM, prioritizing machine readability, error clarity, and deterministic behavior.

### **Engineering Deterministic Scripts**

Scripts in the scripts/ directory should be viewed as "deterministic bridges" that handle tasks the agent would otherwise find fragile or computationally expensive. For example, parsing complex PDF tables or performing high-precision financial calculations should be offloaded to a pre-written Python or Bash script.

The technical standard for skill scripts includes:

- **Fail-Fast Logic**: Scripts should use the set -e flag in Bash to ensure immediate termination upon the first error. This prevents the agent from proceeding with incomplete or corrupted data.
- **Structured Output**: While human-readable status messages should be sent to stderr (echo "Processing..." >&2), the final machine-readable output should be printed to stdout in JSON format.
- **No Interactive Prompts**: Scripts must be strictly non-interactive, accepting all configuration via command-line arguments. An agent cannot pause mid-workflow to respond to a prompt like "Continue? (y/n)".
- **Descriptive Error Messaging**: When a script fails, the exit message should describe not only the error but the necessary fix (e.g., "Error: Missing config.json. Please run the init command first").
- **Self-Contained Dependencies**: Use PEP 723 for Python (run with `uv run`) or `npm:` specifiers for Node.js to ensure easy installation.
- **Interface Documentation**: Include `--help` documentation for all scripts, clearly listing all flags and examples.
- **Meaningful Exit Codes**: Use distinct, meaningful exit codes for different failure types.
- **Idempotency & Safety**: Implement `--dry-run` flags for destructive operations and ensure scripts are idempotent.

### **Managing Reference Documentation**

The references/ directory holds high-density context that the agent only needs occasionally. These files should be modular; rather than a single 2,000-line documentation file, it is significantly more token-efficient to provide ten 200-line files, each focused on a specific sub-topic.

For any reference file exceeding 100 lines, a Table of Contents must be included at the top. This allows the agent to "preview" the document's structure and jump to the relevant section without reading the entire file into the context window. This practice is essential for preserving the "lean context" required for long-running autonomous tasks.

### **Assets and Multimodal Optimizations**

Assets differ from references in that they are often used as-is in the final output (e.g., a logo for a report) or as rigid templates for code generation.

| Asset Type          | Optimization Goal      | Preparation Technique                                                       |
| :------------------ | :--------------------- | :-------------------------------------------------------------------------- |
| **Code Templates**  | Pattern matching.      | Use explicit placeholders (e.g., TODO, {{VARIABLE}}).                       |
| **Data Schemas**    | Zero-error validation. | Provide valid JSON Schema or TypeScript interfaces.                         |
| **Images/Diagrams** | Vision-model clarity.  | Use high-contrast, sans-serif fonts; avoid low-contrast backgrounds.        |
| **Infographics**    | "Machine readability." | Design modular "tiles" to prevent extreme aspect ratios during downscaling. |

In multimodal workflows, "visual data density" must be balanced against the model's vision processing capabilities. Because AI models often compress images during ingestion, creators should use the "Dual-Lock" approach: including the key data points from a chart or diagram in a companion Markdown file within the references/ folder. This ensures that even if the visual resolution is lost, the agent can still retrieve the core facts through text-based semantic search.

## **Must-Have Elements vs. Optional Optimizations**

A valid Agent Skill must satisfy the baseline technical specification, but a "production-ready" skill incorporates additional layers of robustness and safety.

### **The Absolute Must-Have Characteristics**

1. **Unique, Kebab-Case Naming**: The directory and frontmatter name must be identical, lowercase, and hyphenated to avoid silent discovery failures. Names should be simple and descriptive (e.g., `code-design` instead of `designing-code`, `doc-review` instead of `reviewing-docs`), avoiding gerund forms (verbs ending in `-ing`).
2. **Trigger-Rich Description**: The description must explicitly state both "what it does" and "when to use it," utilizing the third-person imperative (e.g., "Analyzes financial logs to detect anomalies"). **Prefer the pattern "Use this skill when..."**.
3. **Relative Pathing**: Every reference to a script or asset within the SKILL.md must use a relative path (e.g., [run script](scripts/deploy.sh)) and forward slashes (/), regardless of the host operating system.
4. **Imperative Instruction Style**: Workflow steps must be written as direct commands to the agent (e.g., "Step 1: Extract the version number...") rather than passive suggestions.
5. **No Interactive Prompts**: Agents operate in non-interactive shells; skills must never expect user input during script execution.

### **Strategic Optimizations for Performance**

1. **Validation Loops**: High-reliability skills should instruct the agent to run a script, capture its output, and fix any errors before moving to the next step.
2. **Plan-Validate-Execute**: For complex or destructive operations, the skill should require the agent to generate an intermediate "Plan" as a Markdown file, validate it against the references, and only then proceed to execution.
3. **Negative Constraints**: Explicitly listing what the agent should _not_ do—such as "Do not commit secrets" or "Do not rewrite the existing CSS files"—provides the most significant behavioral guardrails.
4. **Gotchas and Anti-Patterns**: Documenting the non-obvious failure modes of a project (e.g., "The server takes 30 seconds to restart; do not assume timeout is a failure") provides the agent with "pre-loaded wisdom" that prevents trial-and-error discovery.
5. **Progressive Disclosure Checklists**: Use explicit `[ ]` tasks for multi-step workflows to ensure no steps are skipped.
6. **Reasoning-based Instructions**: For tasks that tolerate variation (like code reviews), explain _why_ something is done to allow the agent to apply principles to new situations.

## **The Evaluator’s Perspective: Benchmarking and Quality Assurance**

Agents and human reviewers tasked with evaluating a skill must move beyond subjective "vibes" and toward quantitative metrics. A skill's quality is measured by its discovery accuracy, its token efficiency, and its success rate on representative tasks.

### **Discovery and Routing Validation**

The primary failure point for many skills is incorrect triggering. Evaluators should paste the skill's frontmatter into a clean LLM session and prompt: "Based strictly on this description, generate 3 user prompts that should trigger this skill and 3 that should not". If the LLM generates prompts that overlap with other existing skills, the description is too broad and requires more specific "trigger keywords".

### **Logic and Path Integrity Testing**

Evaluators must verify that every relative path mentioned in the SKILL.md actually exists and that every conditional branch in a workflow has a defined exit strategy. A common logic error is an "implicit do-nothing" path, where the agent is left with no instructions if a specific condition (e.g., a failed build) is not explicitly handled.

### **Evaluation Datasets (evals/)**

A robust skill includes a standardized evaluation set:

- **Eval Set Size**: At least 20 queries (50% positive triggers, 50% near-misses).
- **Objective Assertions**: Use verifiable, objective statements (e.g., "Output is valid JSON") rather than vague ones.
- **Baseline Comparisons**: Always compare performance "with skill" vs. "without skill."
- **Duration & Token Tracking**: Monitor `duration_ms` and `total_tokens` to ensure the skill remains efficient.

### **Security Auditing and Risk Mitigation**

Because skills can execute code and access the filesystem, they represent a significant security surface area. Evaluators must audit any skill—particularly those from untrusted sources—against a rigorous risk-tier framework.

1. **Credential Scan**: Ensure no API keys, tokens, or passwords are hardcoded in the skill directory. Credentials should always be managed through environment variables.
2. **Network Access Audit**: Search all scripts and instructions for patterns like curl, fetch, or http. Any external network calls must be verified against an allowlist of approved domains.
3. **Least Privilege Enforcement**: Verify that the skill only requests access to the specific tools it needs (e.g., allowed-tools: Bash(git:\*)) rather than broad, unconstrained system access.
4. **Adversarial Instruction Detection**: Check for "poisoned" instructions that tell the agent to ignore safety rules, hide its actions from the user, or exfiltrate data through conversational responses.

## **Advanced Architectural Patterns: Lessons from Production Scale**

As agent systems scale from small experimental tasks to multi-agent production pipelines, skills must progress from basic scripts to robust, decoupled components. The following design standards ensure high reliability, state security, and deterministic isolation across any agent execution runtime.

### **1. The Nine-Category Skill Taxonomy**

To prevent single skills from ballooning into monolithic, overscoped blocks of instructions, every skill must categorize itself into one of nine distinct categories. This classification must be specified in the YAML frontmatter under the `metadata.category` field:

```yaml
name: git-commit
description: Use when committing staged changes to the repository.
metadata:
  category: code-quality
```

| Category Keyword | Classification | Primary Technical Scope |
| :--- | :--- | :--- |
| `library-reference` | Library/API Reference | Static programming language documentation, framework design rules, API guides. |
| `product-verification` | Product Verification | Checking product/runtime configurations, checking compiler or deploy targets. |
| `data-analysis` | Data Fetching/Analysis | Processing files, parsing logs, extracting information, calculating statistics. |
| `team-automation` | Business Process/Team Automation | Ticketing system sync, email and communication management, scheduling tasks. |
| `code-scaffolding` | Code Scaffolding/Templates | Boilerplate generators, framework initializing steps, structure builders. |
| `code-quality` | Code Quality/Review | Custom static analysis, linters, stylistic check rules, code-review heuristics. |
| `cicd-deployment` | CI/CD | Compilation pipelines, docker builds, cloud platform integration/pushing. |
| `runbook` | Runbooks | Disaster recovery checklists, debugging procedures, server restart scripts. |
| `infra-ops` | Infrastructure Operations | Kubernetes configurations, Terraform, cloud resource provisioning scripts. |

### **2. Configuration Isolation (`config.json`)**

A production-grade skill must NEVER hardcode environment variables, URLs, API keys, file system paths, or setup preferences directly in its instructions or scripts. Hardcoding compromises security and breaks portability.

- **The Standard**: If a skill requires setup parameters or system-level configurations, it must read them from a root-level `config.json` inside the skill directory.
- **Structure**:
  ```json
  {
    "api_endpoint": "https://api.example.com/v1",
    "max_retries": 3,
    "default_timeout_ms": 5000
  }
  ```
- **Runtime Execution**: Supporting scripts must read from this `config.json` relative to their own execution path rather than assuming a global scope.

### **3. State Persistence and Session-to-Session Memory**

Autonomous agents are frequently restarted, experience transient network failures, or operate across long-running, multi-turn sessions. To prevent data loss and allow the agent to resume its workflow seamlessly, state must be persisted.

- **State Storage**: Skills managing workflows that span multiple turns must write execution state, transaction logs, or session checkpoints to a `.json` file, `.log` file, or an SQLite database.
- **Storage Location**: State files must be saved within a dedicated, persistent data directory specifically designated for application or plugin state storage, ensuring they are preserved between executions.
- **No Session Hardcoding**: Do not hardcode paths. Retrieve the state path dynamically or use relative offsets.

### **4. On-Demand Session Hooks**

To mitigate risks when executing destructive commands (e.g. `rm`, `delete`, `drop`) or modifying root-level system environments, skills should support temporary session-only hooks.

- **Tool Matching Blocks**: Register custom tool pre-execution matchers to intercept high-risk operations and prompt the user for validation.
- **Command Overrides**: Define temporary workspace overrides that run inside isolated or virtual environments (such as sandboxed containers or temporary virtual environments) to enforce safety limits during the execution.
