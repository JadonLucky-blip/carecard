# Credits / Third-Party Licenses

Every open-source library CareCard depends on, and its license. Verified
against the actually-installed packages (`pip show`, and each npm
package's own `package.json`) on 2026-10-25, not compiled from memory.

## Backend (Python)

| Library | Purpose | License |
|---|---|---|
| FastAPI | web API framework | MIT |
| Uvicorn | ASGI server | BSD-3-Clause |
| Pydantic | data validation / schema | MIT |
| python-multipart | file upload parsing for FastAPI | Apache-2.0 |
| pytesseract | Python wrapper around Tesseract | Apache-2.0 |
| Tesseract OCR | the OCR engine itself (installed separately, not pip) | Apache-2.0 |
| OpenCV (opencv-python-headless) | image preprocessing | Apache-2.0 |
| Pillow | image I/O | MIT-CMU |
| NumPy | array operations backing OpenCV | BSD-3-Clause |
| Anthropic Python SDK | Claude API client | MIT |
| RapidFuzz | fuzzy string matching (grounding validator) | MIT |
| pytest | testing | MIT |
| httpx | test client for FastAPI | BSD-3-Clause |

## Frontend (npm)

| Library | Purpose | License |
|---|---|---|
| React / React DOM | UI framework | MIT |
| TypeScript | type-checked JS | Apache-2.0 |
| Vite | build tool / dev server | MIT |
| @vitejs/plugin-react | React support for Vite | MIT |
| Tailwind CSS / @tailwindcss/vite | styling | MIT |
| vite-plugin-pwa | PWA manifest + service worker | MIT |
| oxlint | linter (scaffold default) | MIT |

## APIs used (not libraries, no license file, but worth disclosing)

| Service | Purpose | Notes |
|---|---|---|
| Anthropic Claude API | structured extraction from redacted text | paid per-request; API key kept server-side only |
