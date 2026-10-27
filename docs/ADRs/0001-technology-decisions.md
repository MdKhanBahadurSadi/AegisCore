# ADR 0001: Working technology selections

- **Status:** Accepted as the user-selected working implementation baseline; the Phase 6A Python environment and minimal FastAPI slice are implemented and tested, while the rest of the stack remains unvalidated.
- **Date:** 2026-10-27
- **Decision owners:** User-provided Master Prompt Pack; future technical compatibility review remains pending.
- **Related:** `docs/Thesis_Proposal.pdf`, `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, [ADR 0002](0002-safety-policy-and-provider-egress.md).

## Context

The thesis proposal defines research scope and permits several implementation alternatives. It says a stateful workflow such as LangGraph may be used, ChromaDB or a similar vector store may be used, and a local or otherwise authorized LLM may be selected after feasibility testing. It names a local Docker instance of OWASP Juice Shop as the primary target. It does not specify a web frontend, FastAPI, Gemini, Docker Compose, or pytest/Flutter test tooling. It lists JSON/CSV/SQLite as possible finding/log outputs but does not require SQLite as the system’s metadata database.

The Master Prompt Pack selects a concrete stack for this project. That selection is binding project direction, but it must not be reported as a thesis requirement or as a verified compatibility result. Docker, LangGraph, and a Gemini SDK were not available in the earlier inspected environment. Before Phase 6A, only the in-memory safety-contract package and tests existed; Phase 6A has since added a minimal read-only API and locked Python dependency environment. The UI, workflow, provider, and database remain unimplemented.

## Decision

| Concern | Working project selection | Classification relative to proposal | Validation status |
|---|---|---|---|
| Web client | Flutter Web | Project choice from Master Prompt; thesis does not specify a frontend. | Not implemented; `flutter doctor` lists Edge, no project exists. |
| API/backend | Python + FastAPI | Project choice from Master Prompt; thesis does not specify language/framework. | Minimal read-only API implemented and tested in the project-local Python 3.13.2 environment. Exact lock versions are recorded below; no operational API or target dispatch route exists. |
| Python dependency management | `uv`, `pyproject.toml`, `uv.lock`, and a project-local `.venv` | Phase 6A implementation choice; neither the proposal nor Master Prompt specifies a Python package manager. | Environment and lock created; install/dependency consistency and Python 3.13.2 test suite verified locally. |
| Workflow orchestration | LangGraph | Project choice from Master Prompt and explicitly proposal-permitted option; proposal also permits equivalent stateful frameworks. | LangGraph package absent; APIs/version not checked. |
| Run/finding/audit metadata | SQLite initially | Project choice from Master Prompt; proposal lists SQLite as one possible output form but does not mandate this database design. | No schema/app exists. |
| Vector retrieval | ChromaDB | Project choice from Master Prompt and explicitly proposal-permitted option; proposal also allows a similar vector store. | ChromaDB 0.5.0 is ambient only; compatibility and persistence not checked. |
| LLM | Gemini API through provider abstraction | Project choice from Master Prompt; proposal permits a local or authorized LLM and does not name Gemini. | Gemini SDK/key absent from current inspected environment; no call made. |
| Primary local target | OWASP Juice Shop in a local Docker instance | Proposal-supported target and local Docker setup; exact image/version remains unresolved. | Docker command absent; no lab started. |
| Lab packaging | Docker Compose | Project choice from Master Prompt; proposal says local Docker instance but does not specify Compose. | Docker/Compose unavailable; not implemented. |
| Backend tests | pytest | Project choice from Master Prompt; proposal does not mandate this test runner. | pytest 8.4.2 is locked in the dev group and the full suite runs in `.venv`. |
| Flutter checks | `flutter test`, `flutter analyze` | Project choice from Master Prompt; proposal does not prescribe these checks. | Flutter 3.32.8/Dart 3.8.1 available; no Flutter project. |
| Embeddings | No provider selected yet | Open choice; Master Prompt requires an appropriate provider but does not name one; proposal leaves framework/model to feasibility. | Unresolved. |

## Consequences

- Future implementation should use this stack unless the user approves a change. A technology substitution requires an explicit revised decision, not an undocumented silent fallback.
- Before implementation, verify compatible and documented versions against current official documentation and lock them in project manifests.
- The existing safety-policy and guarded-execution modules remain standard-library-only and were not modified in Phase 6A. The local project requires Python `>=3.13,<3.14` and selects Python 3.13.2 through `.python-version`. The locked runtime versions are FastAPI 0.162.0, Pydantic 2.14.1, and Uvicorn 0.54.0. The locked dev versions are pytest 8.4.2 and httpx2 2.16.0. These resolved and passed the Phase 6A in-process tests on Windows/Python 3.13.2; this does not validate other platforms or production deployment.
- Uvicorn is included as the selected ASGI server but was not launched. FastAPI's in-process test client is used for API tests; current Starlette guidance recommends httpx2, which avoids the deprecation warning emitted when the compatibility fallback to plain httpx is used.
- Dependencies were installed only under the project-local `.venv`; no global packages were installed or upgraded. uv's lockfile pins the resolved dependency graph. `uv` itself is an installed development tool, not a project runtime dependency.
- The Master Prompt’s Gemini API choice is a working technology selection only; it does not authorize outbound traffic. The current default-deny posture remains in force, and provider/embedding egress is unresolved as detailed in ADR 0002. No remote call may occur before an explicit, documented approval and network-boundary decision.
- The embedding provider may create the same external-network and data-handling question. No embedding model or provider is implied by choosing ChromaDB.
- Docker Compose remains a packaging decision and must not be represented as mandated by the proposal.
- Phase 6A's API exposes only read-only health/capabilities routes. It does not integrate with or call the safety engine or fake-transport boundary, and does not provide a general-purpose target-operation API.
- The selected dependency versions and tested environment do not make the API production-ready. Authentication, local binding, deployment controls, operational routes, persistent storage, and transport remain unresolved.
- This ADR does not approve lab setup, target registration, dataset preparation, external service egress, credentials, or application implementation.

## Alternatives acknowledged by the proposal

- LangGraph **or equivalent** stateful workflow framework.
- ChromaDB **or similar** vector store.
- Local or otherwise authorized LLM, selected after feasibility testing.
- JSON/CSV/SQLite as possible output formats in the proposal architecture description.

These alternatives remain useful context for a future user-approved technology change, but the working choices above remain in effect for now.
