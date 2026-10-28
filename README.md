# <p align="center"><img src="frontend/assets/images/logo.png" alt="AegisCore Logo" width="120"/></p>
# AEGISCORE AI: Evidence-Grounded Multi-Agent Cybersecurity Evaluation Engine

[![Python Tests](https://img.shields.io/badge/Python-pytest%20(617%20passed)-10B981?style=for-the-badge&logo=python)](pyproject.toml)
[![Flutter Tests](https://img.shields.io/badge/Flutter-100%25%20Passing-06B6D4?style=for-the-badge&logo=flutter)](frontend/pubspec.yaml)

AegisCore is a production-grade, empirical cybersecurity AI research and evaluation engine combining a deterministic multi-agent reasoning backend (Python / FastAPI) with a cybersecurity-themed cross-platform UI (Flutter / Material 3).

---

## 🌟 Key Features

- **Evidence-Grounded Multi-Agent Consensus:** Multi-specialist agent orchestration with adversarial reviewer challenge, citation excerpt verification, and fail-closed abstention guarantees.
- **Strict Uncertainty Aggregation:** Transparent, calibrated uncertainty aggregation engine mapping signal audits to state transitions.
- **Offline Evaluation Harness & Case Catalog:** Canonical vulnerability benchmarks, rigorous scoring metrics (Wilson score confidence intervals, specificity, grounding rate), and reproducible trial replay.
- **Cybersecurity Flutter UI (`frontend/`):** Material 3 dark terminal slate interface (`#0B0F19`) featuring adaptive navigation (`AppScaffold`), live/demo mode switching, evidence explorer, and comprehensive reporting.
- **Fail-Closed Security & Provenance:** Strict SHA-256 evidence digest verification, local SQLite persistence, and zero unverified execution paths.

---

## 🏗️ Project Architecture

```
AegisCore/
├── aegiscore/            # Python backend (FastAPI, RAG, Multi-Agent, Uncertainty Engine)
├── frontend/             # Flutter M3 UI (Riverpod, GoRouter, Cyber theme, 6 core screens)
├── tests/                # Comprehensive Python test suite (617+ tests)
├── test/                 # Flutter widget & state test suite
├── docs/                 # Architectural Decision Records (ADRs) & Threat Models
└── testbed/              # Isolated lab testbed configurations
```

---

## 🚀 Quick Start

### 1. Python Backend & Tests
```powershell
uv sync
pytest
```

### 2. Flutter Frontend & Verification
```powershell
cd frontend
flutter pub get
flutter analyze
flutter test
```

---

## 📚 Documentation
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Threat Model](docs/THREAT_MODEL.md)
- [Test Plan](docs/TEST_PLAN.md)
- [Supervisor Review Package](docs/SUPERVISOR_REVIEW_PACKAGE.md)

---

## 🛡️ License
Distributed under the MIT License.
