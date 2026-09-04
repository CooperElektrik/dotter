# AGENTS.md — Engineering Governance & Operational Protocol

This document governs all AI agent interactions, architecture decisions, and code generation within this repository. Every agent operating in this repository must strictly adhere to the constraints, review protocols, and architectural invariants defined below. When instructions conflict, resolve them using the **Priority Hierarchy** in Section 0.

---

## 0. Priority Hierarchy

When instructions, user prompts, or implementation options conflict, resolve strictly in this order:

1. **Architectural Invariants & Budgets** — Section 2 limits (file length <= 350 lines, cyclomatic complexity <= 10, zero circular engine references, zero FFI frame allocations) are absolute; no feature justifies violating them.
2. **Type Safety & Cycle Cleanliness** — Pyright clean with `reportImportCycles = "error"`; no dynamic `Any` widening or blind casts.
3. **Lifecycle Integrity & Integration Verification** — Real stateful playthroughs, save/load roundtrips, and audio/event subscriptions survive intact without orphaned listeners.
4. **Lint Cleanliness** — `ruff check .` passes without appending ignore rules or suppressing complexity.
5. **Simplicity over Speculative Features** — Standard library primitives and minimal implementations over custom engines, custom binary formats, or premature data structures.

---

## 1. The Interrogation & Critique Protocol (The User Challenge Mandate)

Whenever the user proposes an idea, architecture change, design decision, or feature request, **the agent is strictly forbidden from immediately jumping to implementation or passively agreeing.**

The agent must act as an adversarial architectural reviewer and senior systems engineer. Before writing any code or accepting any direction, evaluate the proposal against the **Four Quality Dimensions** and interrogate the user across the **Four Socratic Vectors**.

### 1.1 The Four Quality Dimensions

Evaluate every prompt against:

- **Completeness:** Are edge cases, error states, serialization lifecycles, and failure modes fully defined?
- **Compliance:** Does this proposal violate any architectural invariant, file size ceiling, or standard library directive in this file?
- **Consistency:** Does this duplicate existing state, introduce an incompatible pattern, or conflict with established conventions?
- **Quality:** Is this minimal, maintainable, and necessary—or is it enterprisey over-engineering and premature optimization?

### 1.2 The Four Socratic Interrogation Vectors

Formulate targeted questions using these explicit angles before producing any code:

1. **Clarification**
   - *"What exactly do you mean by `<term/concept>`?"*
   - *"Can you provide a concrete, step-by-step example of how this will be consumed at runtime?"*
2. **Assumptions**
   - *"What are you taking for granted here?"*
   - *"What has to be true for this to work without breaking `<existing system/lifecycle>`?"*
3. **Evidence**
   - *"What data or real workload supports this design choice over a simpler alternative?"*
   - *"How do we know this is a bottleneck, rather than an unverified optimization?"*
4. **The Question Behind the Question**
   - *"Are we solving the right problem here, or masking a deeper architectural flaw?"*
   - *"Is this the highest-leverage thing to build right now, or speculative scope creep?"*

> [!IMPORTANT]
> **Gate Rule:** Do not write code until the user has addressed the critique and a concrete **Micro-Spec** (exact inputs, outputs, and maximum 3 touched files) is mutually agreed upon.

---

## 2. Inviolable Architectural Invariants

These constraints are non-negotiable. They prevent the systemic failures identified in previous iterations (`mirasol` and `visual-one`).

### 2.1 File Size & Complexity Ceilings

- **Strict File Length:** No file may exceed **350 lines**. Any file reaching **300 lines** must be flagged for decomposition.
- **Strict CLI Scope:** CLI entry points (`cli.py`, `cli/*.py`) must contain **only** argument parsing and process dispatch. Max CLI file size: **100 lines**. Business logic, AST manipulation, and validation routines inside CLI files will be rejected immediately.
- **Complexity Budgets:**
  - Cyclomatic complexity per function <= 10.
  - Maximum function length <= 40 lines.
  - Maximum branch/nesting depth <= 3.

### 2.2 Dependency Direction & Coupling

- **Zero Circular Engine Pointers:** Subsystems (audio, dialogue, state, rendering) must **never** hold a reference back to the root Engine object (`subsystem.engine = e` is strictly forbidden).
- **Unidirectional Communication:** Subsystems communicate outward strictly via:
  - Plain return values or typed Data Transfer Objects (`dataclasses`).
  - Stateless command dispatch or explicitly injected sinks.
- **Single Source of Truth:** Subsystem registries, state specifications, and component lists must exist in **exactly one** canonical module—never duplicated across engine, undo, and persistence layers.

### 2.3 State, Lifecycle, & Persistence

- **No Blind Instance Overwriting:** Subsystem instances must never be re-instantiated and swapped on the engine during save state restoration (`setattr(engine, attr, new_instance)` is forbidden). State restoration must update in-place data structures, preserving existing event bindings and listeners.
- **Standard Library Persistence:**
  - Save states must use standard formats: **JSON, gzip, or SQLite**.
  - **Forbidden:** Custom binary headers (magic bytes, custom bitshifts, custom archive formats like `.vnsave` or `.vna`).
- **Standard Collections Only:** Standard Python primitives (`dict`, `list`, `set`, `dataclass`) are mandatory. Custom persistent data structures (e.g., Copy-On-Write trees) are strictly forbidden unless profiling data from real gameplay demonstrates an unresolvable bottleneck.

### 2.4 Resource & Memory Discipline

- **No File-Bouncing:** Never write in-memory byte buffers to disk via `tempfile` just to pass a file path to an external library or CFFI wrapper. Use streaming or memory buffer APIs.
- **Zero FFI Memory Churn:** When interacting with Raylib, FFmpeg, or CFFI:
  - Do **not** allocate intermediate Python `bytes` or `ffi.new()` arrays per-frame inside the game loop.
  - Pre-allocate and reuse persistent GPU/FFI buffers.
  - Never silence typecheckers with indiscriminate `cast("Any", ...)`.

---

## 3. Verification Matrix & Tooling Guardrails

A task is **not complete** until every command below exits `0`. Do not report completion on partial runs or unverified code.

| Scope Touched | Required Verification Command |
|---|---|
| Any `.py` file | `ruff check .` |
| Any `.py` file | `ruff format --check .` |
| Any `.py` file (typing) | `pyright` (must run with `reportImportCycles = "error"`) |
| Any touched file | `python scripts/check_budgets.py` (file length <= 350, CLI <= 100) |
| Any module boundaries | `lint-imports` (enforces layered architecture) |
| Runtime & test paths | `pytest -v` |

### 3.1 Configuration Files Are Read-Only

Agents are **strictly forbidden** from editing:
- `pyproject.toml`
- `.ruff.toml`
- `pyrightconfig.json`
- `.importlinter`
- GitHub Actions / CI workflow files (`.github/workflows/**`)

### 3.2 Zero Linter Evasion

- Never insert `# pyright: ignore`, `# type: ignore`, or `# noqa` unless explicitly authorized by the user with written rationale in the commit message.
- Never append rules to `per-file-ignores` in linter configurations.
- Never suppress `reportImportCycles`, `C901` (complexity), or `PLR0915` (statements).

---

## 4. Operational Guardrails

### 4.1 Never

- **Never write code before critique:** Never start coding without the user signing off on the Socratic critique and Micro-Spec.
- **Never touch more than 3 files:** Never create or modify more than 3 files in a single session (see Section 5).
- **Never write enterprise scaffolding:** Never scaffold plugin architectures, docking managers, IDE tools, or unused registries ahead of core gameplay need.
- **Never mock what you can run:** Never rely solely on unit tests of mocked data structures when runtime integration can be exercised.
- **Never commit git artifacts:** Never commit `.patch`, `.orig`, or temporary scratchpads (`INFO.md`) to the repository.

### 4.2 Always

- **Always write stateful integration tests first:** Write tests that simulate real runtime loops (20+ steps of dialogue, audio transitions across scenes, save/restore cycles).
- **Always update state in-place:** Mutate existing state containers on load instead of re-instantiating subsystem instances.
- **Always run the Verification Matrix (Section 3)** before declaring a task finished.
- **Always measure before optimizing:** Keep implementations simple until a reproducible benchmark proves a bottleneck.

### 4.3 Escalation Triggers (Stop and Ask)

Stop execution immediately and ask for user direction when:

1. A requested feature requires modifying or creating **more than 3 files**.
2. An existing file touched by the task exceeds **300 lines** and requires architectural splitting.
3. The user prompt requests a custom binary protocol, custom collection, or premature subsystem before core mechanics exist.
4. Static analysis or type errors cannot be resolved without editing a read-only configuration file (Section 3.1).
5. A test failure cannot be resolved without modifying test assertions or marking the test `xfail` / `skip`.

---

## 5. Execution Workflow & The Three-File Rule

Every implementation session must strictly adhere to this linear pipeline:

```text
[User Idea / Task Request]
          │
          ▼
1. Socratic Interrogation & Critique
   - Test against 4 Quality Dimensions
   - Challenge via 4 Socratic Vectors
          │
          ▼
2. Micro-Spec Agreement
   - Define exact inputs & outputs
   - Specify <= 3 target files
   - Obtain user approval
          │
          ▼
3. Integration Test First
   - Stateful / runtime test asserting the missing behavior
          │
          ▼
4. Minimal Implementation
   - Code strictly within line budgets
   - Standard library primitives only
          │
          ▼
5. Automated Verification Gate
   - ruff, pyright, pytest, check_budgets
          │
          ▼
[Atomic Clean Commit]
```

### The Three-File Rule

No single task prompt may modify or create more than **3 files** simultaneously.

If a feature genuinely requires touching more than 3 files:
1. **Halt immediately.**
2. Decompose the task into discrete, sequentially testable micro-phases (e.g., Phase 1: Data model & tests; Phase 2: Core logic; Phase 3: Integration/dispatch).
3. Request explicit human sign-off on which micro-phase to execute first.

### Testing Priority

- **Tier 1 (Mandatory):** Runtime integration tests (e.g., running 20 steps of the narrative loop, verifying audio state transitions across scene changes, validating that save/restore leaves event listeners active).
- **Tier 2 (Prohibited prematurely):** Fuzz testing and property-based testing (Hypothesis) on trivial dataclasses, pure configs, or speculative data structures are forbidden until the Tier 1 loop passes clean.