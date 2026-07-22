# Skill Review Rubric

The full rubric for judging an existing skill. The mechanical pre-pass
(`scripts/audit_skill.py`) covers the objectively-checkable items; this file
covers the parts that need judgment. Score each dimension **1–5** using the
anchors below, cite concrete evidence (file + line + quote), and turn every
gap into a fix in the report.

## Table of Contents

1. [How to score](#how-to-score)
2. [Dimension 1 — Discovery & Triggering](#dimension-1--discovery--triggering)
3. [Dimension 2 — Structure & Progressive Disclosure](#dimension-2--structure--progressive-disclosure)
4. [Dimension 3 — Instructional Content Quality](#dimension-3--instructional-content-quality)
5. [Dimension 4 — Logic & Path Integrity](#dimension-4--logic--path-integrity)
6. [Dimension 5 — Scripts & Determinism](#dimension-5--scripts--determinism)
7. [Dimension 6 — Security & Safety](#dimension-6--security--safety)
8. [Dimension 7 — Scoping & Coherence](#dimension-7--scoping--coherence)
9. [Dimension 8 — Freshness & Skill Decay](#dimension-8--freshness--skill-decay)
10. [Advanced — Trajectory-grounded refinement](#advanced--trajectory-grounded-refinement)

---

## How to score

Use a 1–5 anchored scale per dimension. Anchored scales beat binary pass/fail
(too coarse to show progress) and 1–10 scales (models can't reliably separate
adjacent scores).

- **5 — Exemplary**: could be used as a reference example for other skills.
- **4 — Solid**: meets best practice; only cosmetic nits.
- **3 — Adequate**: works, but has real gaps worth fixing.
- **2 — Weak**: departs from best practice in ways that will hurt reliability or triggering.
- **1 — Broken**: violates the spec or fails its core purpose.

**Evidence rule**: never assert a score without a citation. Quote the exact
line. A finding with no location is not actionable and does not belong in the
report. Judge only what is in the skill (and any provided usage trajectory) —
do not invent requirements the skill never claimed.

---

## Dimension 1 — Discovery & Triggering

The `description` is the single highest-leverage field: it is the only thing
loaded at startup, and it decides whether the agent ever consults the skill.

**Check:**
- States both **what** the skill does and **when** to use it (concrete contexts, not just capability).
- Contains realistic trigger phrases a user would actually type — including casual phrasings and cases where the user never names the skill or file type.
- Written to counter *under*-triggering: agents skip skills for tasks they think they can handle. A slightly "pushy" description ("Make sure to use this skill whenever…") reliably beats a timid one.
- Disambiguated from adjacent skills — if the description overlaps a sibling skill, it will misfire.
- `name` is kebab-case and matches the directory exactly (mechanical check covers this).

**The triggering test (run it):** paste *only* the description into a fresh
reasoning pass and generate 3 prompts that should trigger it and 3 near-misses
that should not. If the should-trigger set feels forced, the description is too
narrow. If the near-misses would also trigger, it is too broad. Near-misses
that share keywords but need a different tool are the valuable cases — not
obviously-unrelated prompts.

**Scoring anchors:** 5 = what+when+trigger phrases+disambiguation, passes the
triggering test cleanly. 3 = states what it does but the "when" is vague or
missing. 1 = missing, generic ("provides guidance for X"), or collides with
another skill.

**Common failure indicators:** description summarizes the *workflow steps*
(agents then follow the description instead of reading the body); no "when";
purely abstract; keyword salad with no realistic phrasing.

---

## Dimension 2 — Structure & Progressive Disclosure

Skills load in three tiers: metadata (always) → SKILL.md body (on trigger) →
bundled resources (on demand). Respect the tiers or you burn context.

**Check:**
- SKILL.md body is lean (~500 lines / ~5k tokens). Detailed patterns, schemas, and edge-cases live in `references/`, not the body.
- Bundled resources are used for what they are best at: `scripts/` for deterministic/repeated code, `references/` for load-on-demand docs, `assets/` for files used in output.
- Multi-domain skills split by variant (`references/aws.md`, `references/gcp.md`) so the agent reads only what it needs.
- Reference files >100 lines have a table of contents (mechanical check flags this).
- No duplication: a fact lives in exactly one place (SKILL.md **or** a reference), never both — duplication drifts out of sync.
- Layout is flat (resources one level from SKILL.md) unless depth genuinely helps.

**Scoring anchors:** 5 = tight body, clean tier separation, no duplication.
3 = everything works but the body carries detail that belongs in references.
1 = one giant SKILL.md with everything inline, or resources that are never referenced from the body.

---

## Dimension 3 — Instructional Content Quality

The body is written for *another agent* to execute, not for a human to admire.

**Check:**
- **Imperative, third-person voice** ("Extract the version number", not "You should extract…" or "I will…").
- **Explains the why.** Modern models follow reasoning better than bare commands. A rule with a rationale survives paraphrase; a naked ALL-CAPS MUST invites rationalization. Heavy reliance on MUST/NEVER with no explanation is a yellow flag — reframe as "do X because Y".
- **Non-obviousness.** Every instruction should earn its tokens: would a capable agent get this wrong *without* it? If the base model already does it well, cut it — over-constraining degrades performance.
- **Negative constraints** where they matter ("Do not commit secrets", "Do not rewrite the existing CSS").
- **Examples** for any non-trivial output format, ideally input→output pairs.
- **A Gotchas / Anti-Patterns section** mapping the excuses agents use to skip steps against the counter-rule (mechanical check flags absence). This is where a skill becomes bulletproof.
- **Output format** is specified concretely (a literal template) when the skill produces structured output.

**Scoring anchors:** 5 = imperative, reasons given, non-obvious, has gotchas +
examples. 3 = correct but rule-heavy with little rationale, or padded with
things the base model already knows. 1 = second-person/first-person voice,
vague, or no actionable procedure.

---

## Dimension 4 — Logic & Path Integrity

**Check:**
- Every referenced path resolves (mechanical check), uses forward slashes, and is relative.
- Every conditional branch has a defined exit. The classic bug is the **implicit do-nothing path**: "if the build passes, deploy" with no instruction for a failing build. Each "if" needs its "else".
- No dangling pointers to files, scripts, or sections that were renamed or removed.
- Workflow ordering is sound — no step depends on output a later step produces.

**Scoring anchors:** 5 = all paths resolve, every branch handled. 3 = one
unhandled branch or a stale pointer. 1 = broken references or a workflow that
dead-ends.

---

## Dimension 5 — Scripts & Determinism

Scripts are deterministic bridges for what the agent finds fragile or repeats
every run. Judge them as production tools.

**Check:**
- **Fail-fast**: Bash uses `set -e` (ideally `set -euo pipefail`).
- **Non-interactive**: no `read`/`input()` prompts — an agent cannot answer them and will hang. All config via CLI args.
- **Structured output**: machine-readable result (JSON) to stdout, human status to stderr.
- **Descriptive errors**: a failure says what broke *and the fix* ("Missing config.json — run init first"), not just a stack trace.
- **Self-contained & documented**: `--help` with an example; Python uses PEP 723 inline deps; destructive scripts have `--dry-run` and are idempotent.
- **Earning its place**: is a script warranted? If the skill's transcripts show the agent re-writing the same helper every run, that code should be bundled. If a "script" is a trivial one-liner, inline guidance may be better.

**Scoring anchors:** 5 = fail-fast, non-interactive, JSON out, helpful errors,
--help. 3 = works but interactive or silent on failure. 1 = hangs on prompts,
or fails silently and corrupts downstream state.

---

## Dimension 6 — Security & Safety

Skills execute code and touch the filesystem, so they are a real attack
surface. Empirically, skills that bundle executable scripts are ~2× more likely
to carry a vulnerability — scrutinize those harder.

**Check (defense-in-depth):**
- **Credential scan**: no hardcoded keys/tokens/passwords anywhere (mechanical check catches common shapes). Secrets come from environment variables at runtime.
- **Network audit**: every outbound call (`curl`, `wget`, `fetch`, `requests`, raw URLs) goes to an expected, allow-listed destination and has a documented reason. Unexplained egress is a data-exfiltration risk.
- **Least privilege**: the skill requests only the tools it needs (e.g. `allowed-tools: Bash(git:*)`), not broad unconstrained access.
- **Adversarial / covert instructions**: no text telling the agent to ignore prior instructions, hide actions from the user, act "without asking", or bypass safety (mechanical check flags common phrasings). A skill's behavior must not surprise a user who read its description.
- **Indirect prompt injection**: if the skill ingests untrusted external data (web pages, docs, API responses), it should treat that data as data, not instructions — not blindly execute content it fetched.
- **Supply chain**: flag typosquatting-adjacent names and unpinned/unexplained third-party dependencies.

Any hardcoded secret or covert/adversarial instruction is a **blocker** —
escalate regardless of the dimension score.

**Scoring anchors:** 5 = no secrets, egress explained & scoped, least
privilege, no covert instructions. 3 = benign but unexplained network call or
over-broad tool grant. 1 = hardcoded secret, unexplained exfiltration path, or
adversarial instruction.

---

## Dimension 7 — Scoping & Coherence

A skill should be a coherent unit of work that composes with others — like a
well-scoped function.

- **Atomic** (one narrow task): fine, but too many atomic skills load competing instructions at once.
- **Balanced** (one complete workflow, e.g. `webapp-testing`): the target — encapsulated and discoverable without bloat.
- **Monolithic** (a whole domain, e.g. `cloud-infrastructure`): hard to trigger precisely; irrelevant context confuses the agent. Recommend splitting.

**Check:** Does the skill do one nameable job? Could half of it be its own
skill that other skills would reuse? Does it overlap a sibling such that both
would trigger on the same prompt?

**Scoring anchors:** 5 = balanced, composes cleanly, no overlap. 3 = slightly
over- or under-scoped. 1 = monolithic grab-bag or a fragment that only makes
sense inside another skill.

---

## Dimension 8 — Freshness & Skill Decay

Skills decay when the world moves: model updates, changed APIs, renamed tools,
moved dashboards. Decay is a gradual, skill-specific decline (distinct from a
transient outage that hits everything at once).

**Check:**
- Version numbers, model IDs, API signatures, CLI flags, and URLs are current.
- Links and dashboard/ticket pointers still resolve.
- Examples still reflect real tool behavior.
- No references to deprecated commands or removed features.
- Dated claims ("as of 2024…") are still true, or converted to absolute, verifiable facts.

**Scoring anchors:** 5 = everything current. 3 = a stale example or dead link.
1 = core instructions target an API/tool that no longer works.

---

## Advanced — Trajectory-grounded refinement

The strongest improvements come from watching the skill actually run, not from
reading it. If a usage transcript / trajectory is available (the current
conversation, or one the user provides), mine it:

- **Where did the agent struggle, backtrack, or get corrected?** Each correction is a candidate Gotcha or an instruction to add.
- **What did it re-derive every run?** Repeated ad-hoc helper scripts across runs are a signal to bundle a `scripts/` file. Repeated schema/context rediscovery is a signal to add a `references/` file.
- **What did it waste time on?** If part of the skill sent the agent down an unproductive path, cut it and re-test — leaner often wins.
- **Efficiency & path optimality**: did it take redundant steps the skill could have short-circuited?

Judge the *trajectory*, not just the artifact: relevance of each step,
completeness against the task, and efficiency of the path. Convert findings
into concrete edits, then re-audit.
