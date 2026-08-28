# SBOM — Software Bill of Materials

## 1. SBOM Scope & Method

**Scope:** Application source code (`fetch_eits.py`) and the Python runtime environment recorded in `pyvenv.cfg`.

**What is included:**
- Python runtime version
- Python standard library modules imported by the application
- Development tooling present in the virtual environment (`lib/` directory)

**What is excluded:**
- Transitive standard library internals (not enumerable without runtime inspection)
- Operating system libraries

**How dependencies were identified:**
- Import statements in `fetch_eits.py` (direct standard library usage)
- `pyvenv.cfg` (Python version)
- `lib/python3.13/site-packages/` directory listing (installed packages in venv)

---

## 2. SBOM Summary

| Attribute | Value |
|---|---|
| Programming language | Python 3.13 |
| Package manager | None (stdlib only at runtime) |
| Direct runtime dependencies | 0 third-party packages |
| Direct build/dev dependencies | 1 (pip) |
| Transitive dependencies | 0 (stdlib has no external transitive deps) |

---

## 3. Component Inventory

### 3a. Runtime — Python Standard Library (direct imports)

| Component Name | Version | Type | Source | Scope |
|---|---|---|---|---|
| Python | 3.13.12 | Runtime | System (`/usr/bin/python3.13`) | Runtime |
| `argparse` | (stdlib) | Library | CPython stdlib | Runtime |
| `concurrent.futures` | (stdlib) | Library | CPython stdlib | Runtime |
| `csv` | (stdlib) | Library | CPython stdlib | Runtime |
| `html` | (stdlib) | Library | CPython stdlib | Runtime |
| `html.parser` | (stdlib) | Library | CPython stdlib | Runtime |
| `json` | (stdlib) | Library | CPython stdlib | Runtime |
| `sys` | (stdlib) | Library | CPython stdlib | Runtime |
| `time` | (stdlib) | Library | CPython stdlib | Runtime |
| `urllib.request` | (stdlib) | Library | CPython stdlib | Runtime |

### 3b. Development / Build Tooling (virtual environment only)

| Component Name | Version | Type | Source | Scope |
|---|---|---|---|---|
| pip | 26.0.1 | Tool | PyPI | Build-time |

pip is present in the virtual environment as installed tooling. It is not imported or used at runtime by the application.

---

## 4. Third-Party Services & Platforms

| Service | Purpose | Endpoint |
|---|---|---|
| E-ITS REST API | Source of all framework data fetched by the application | `https://eits.ria.ee/api/2` |

This is a public REST API operated by RIA (Riigi Infosüsteemi Amet / Estonian Information System Authority). It is not a library dependency but is a required external platform for the application to function.

---

## 5. Known Gaps & Limitations

- **No lockfile or manifest:** The application has no `requirements.txt`, `pyproject.toml`, or `pip.lock`. This is intentional — there are no third-party runtime dependencies to pin.
- **Standard library versions are not independently versioned:** stdlib module versions are tied to the Python runtime version (`3.13.12`) and cannot be listed separately.
- **Transitive stdlib dependencies:** The CPython standard library has internal interdependencies that are not enumerated here; they are considered part of the Python runtime component.
- **Operating system libraries:** System-level libraries (e.g. `libssl`, `libpython`) used by the Python runtime are outside the scope of this SBOM.

---

## 6. SBOM Format & Usage Notes

- This SBOM is a **human-readable Markdown representation** of the software bill of materials derived from static analysis of the repository.
- It can serve as a baseline for generating machine-readable SBOM formats such as **SPDX** or **CycloneDX**.
- For release pipelines, automated SBOM tooling (e.g. `syft`, `cyclonedx-bom`, `pip-audit`) is recommended to complement this document and enumerate transitive OS-level dependencies.
- This document reflects the state of the repository at the time of generation and should be regenerated when dependencies change.
