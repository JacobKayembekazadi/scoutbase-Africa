# ScoutBase Africa — Ralph Loop #4: 14-Layer System Architecture Audit
## Applied Framework: System Architect v2026 × Systems Thinking × First Principles × Second-Order Thinking

**Date:** 2026-02-13  
**Analyst:** System Architect v2026  
**Scope:** Blind spots NOT covered in RL1-RL3 — applying all 14 architecture layers

---

## 🔬 Methodology

Previous Ralph Loops focused on **code-level bugs and emergent fix-interactions**.  
RL4 shifts perspective to the **14 architectural layers**, asking:  
*"What systemic blind spots exist when we evaluate ScoutBase through each layer?"*

Each issue maps to one or more of:
- **Layer 3: Failure Map** — What breaks and what catches it?
- **Layer 6: Validation Schema** — What gates data quality?
- **Layer 8: Persistence** — How does data survive?
- **Layer 9: Security** — Who can access what?
- **Layer 10: Resilience** — What works without network?
- **Layer 12: Accessibility** — Can everyone use it?
- **Layer 13: Evolution** — How do we ship changes?
- **Layer 14: Experience** — How does it feel?

---

## 🚨 Issues Found

### RL4-1: Path Traversal via `video.filename` [SECURITY — Layer 9]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | `video.filename` (user-supplied) is injected directly into `UPLOAD_DIR / f"{job_id}_{video.filename}"`. A filename like `../../etc/passwd` could write outside the uploads directory |
| **First Principles** | Never trust user-supplied filenames — they are untrusted input |
| **Second-Order** | An attacker could overwrite `server.py`, `data/server_state.json`, or `.env` — gaining full control |
| **Systems Impact** | Affects every downstream path: `results_path`, frame extraction, CSV download |
| **Fix** | Sanitize filename using `Path(video.filename).name` to strip directory components, and validate it contains only safe characters |
| **Status** | ✅ FIXED |

### RL4-2: Live API Token Committed in `.env` [SECURITY — Layer 9]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | `.env` file contains a real `HF_TOKEN=hf_REDACTED`. While `.gitignore` includes `.env`, the token is live in the working directory |
| **First Principles** | Secrets should never exist as plaintext in any file that might be shared or copied |
| **Second-Order** | If the project is zipped/shared (as "africa vision os"), the token travels with it. Anyone with the token can access HuggingFace models and incur costs under the user's account |
| **Fix** | Replace live token with placeholder in `.env`, add `SECURITY.md` documentation advising token rotation |
| **Status** | ✅ FIXED |

### RL4-3: No Input Validation on Player Data [VALIDATION — Layer 6]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | `PlayerBase` model accepts any string for `verificationStatus`. The check constraint exists in `schema.sql` but NOT enforced in the API Pydantic model |
| **First Principles** | Validation should happen at every boundary — not just the database |
| **Second-Order** | Invalid status values like `"hack"` pass through API → break `VerificationBadge` rendering (silent fallback to "unverified" config, but data is corrupted) |
| **Fix** | Add `Literal` type constraint to `verificationStatus` and range validation to scores |
| **Status** | ✅ FIXED |

### RL4-4: `video.filename` Unsanitized in Response Headers [SECURITY — Layer 9]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | `video.filename` is stored directly in `jobs[job_id]["video_filename"]` and could contain characters that break HTTP headers or enable header injection |
| **First Principles** | All user input in HTTP responses must be sanitized |
| **Second-Order** | Header injection could lead to response splitting attacks in certain proxy configurations |
| **Fix** | Sanitize stored filename alongside path construction |
| **Status** | ✅ FIXED (via RL4-1 sanitization) |

### RL4-5: `results_path` Used Without Containment Check [SECURITY — Layer 9]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | `results_path` from job data is used directly in `Path(job["results_path"])` for serving files. If state file is tampered with (RL3-6), arbitrary files could be served |
| **First Principles** | File-serving endpoints must validate that resolved paths stay within expected directories |
| **Second-Order** | Combined with state file corruption, an attacker could read any file on the server filesystem |
| **Fix** | Add path containment validation — resolved path must start with `RESULTS_DIR` |
| **Status** | ✅ FIXED |

### RL4-6: Upload/SAM3 Sections Skip `!loading && !error` Guards [EXPERIENCE — Layer 14]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | In `page.tsx`, sections `upload` and `sam3` render without `!loading && !error` checks (lines 307-313), unlike all other sections |
| **First Principles** | Conditional rendering should be consistent across all branches |
| **Second-Order** | When initial data fetch fails, upload/SAM3 sections still render — but they depend on API connectivity. Users see a working UI that will immediately fail on any action |
| **Fix** | Add consistent `!loading && !error` guards to upload and SAM3 sections |
| **Status** | ✅ FIXED |

### RL4-7: `compareList` Never Persisted, Lost on Page Refresh [PERSISTENCE — Layer 8]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | `compareList` state is purely in-memory React state with no persistence |
| **First Principles** | User-curated selections should survive navigation/refresh |
| **Second-Order** | A scout carefully selects 4 players for comparison, accidentally refreshes → all work lost. Frustration compounds with daily use |
| **Fix** | Persist `compareList` to `sessionStorage` — survives refresh but clears on tab close (appropriate for short-lived comparison sessions) |
| **Status** | ✅ FIXED |

### RL4-8: `scoutbase-demo.jsx` Dead Code File [EVOLUTION — Layer 13]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | `scoutbase-demo.jsx` exists as a standalone 1500+ line file that predates the React/Next.js refactoring. It's not imported anywhere |
| **First Principles** | Dead code is a maintenance liability — it creates confusion about what's canonical |
| **Second-Order** | New developers may accidentally modify this file thinking it's the source of truth. It also creates false positives in code searches |
| **Fix** | Document as deprecated — renaming to `.deprecated.jsx` to signal intent |
| **Status** | ✅ FIXED |

### RL4-9: Docker `COPY .` Includes `.env` With Secrets [SECURITY — Layer 9]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | Dockerfile `COPY . .` copies everything including `.env` file with live tokens into the Docker image |
| **First Principles** | Docker images are immutable artifacts that may be pushed to registries — secrets in images are exposure vectors |
| **Second-Order** | If the Docker image is pushed to Docker Hub or shared, the HF token is permanently embedded in a layer |
| **Fix** | Add `.dockerignore` excluding `.env`, `*.log`, `uploads/`, `results/`, `data/`, `checkpoints/`, `venv/`, `__pycache__/`, `node_modules/` |
| **Status** | ✅ FIXED |

### RL4-10: `docker-compose.yml` Health Check Uses `curl` But Image Has No `curl` [RESILIENCE — Layer 10]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | `docker-compose.yml` healthcheck uses `curl -f http://localhost:8000/health`, but the Dockerfile installs only Python — `curl` is not in the image |
| **First Principles** | Health checks must use tools available in the runtime environment |
| **Second-Order** | Docker reports container as unhealthy → restarts in a loop → cascading service failures |
| **Fix** | Change docker-compose healthcheck to use Python (matching Dockerfile's own HEALTHCHECK) |
| **Status** | ✅ FIXED |

### RL4-11: No Content-Security-Policy or Security Headers [SECURITY — Layer 9]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | API responses have no security headers (CSP, X-Content-Type-Options, X-Frame-Options) |
| **First Principles** | Defense in depth requires multiple security layers |
| **Second-Order** | Without `X-Content-Type-Options: nosniff`, browsers may MIME-sniff served video/frame content as HTML, enabling XSS via uploaded files |
| **Fix** | Add security headers middleware to FastAPI |
| **Status** | ✅ FIXED |

### RL4-12: No Error Boundary in React Application [RESILIENCE — Layer 10]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | No React Error Boundary component exists. Any unhandled JS error in any component crashes the entire app |
| **First Principles** | Error boundaries are React's fault tolerance mechanism — without them, one bad render kills everything |
| **Second-Order** | A single malformed player record (null `stats`, missing `medical`) crashes the entire dashboard — every player becomes inaccessible |
| **Fix** | Add `ErrorBoundary` component wrapping the main content area |
| **Status** | ✅ FIXED |

### RL4-13: `temp_api.json` Files in Project Root [EVOLUTION — Layer 13]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | Two temp JSON files (`temp_api.json`, `CUsersjacobDownloadstemp_api.json`) exist in root — leftovers from development |
| **First Principles** | Project root should contain only intentional files |
| **Second-Order** | These files may contain sensitive API response data and confuse automated tooling |
| **Fix** | Add `*.json` temp files to `.gitignore` pattern, document for cleanup |
| **Status** | 📋 DOCUMENTED (manual cleanup needed) |

### RL4-14: `nul` File in Project Root [EVOLUTION — Layer 13]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | A file literally named `nul` exists — likely from a Windows `> nul` redirection accident |
| **Fix** | Document for manual cleanup |
| **Status** | 📋 DOCUMENTED |

### RL4-15: Keyboard Navigation Not Implemented [ACCESSIBILITY — Layer 12]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | Sidebar items, player rows, and comparison cards use `div` with `onClick` — no `tabIndex`, `role`, or `onKeyDown` handlers |
| **First Principles** | Interactive elements must be focusable and activatable via keyboard |
| **Second-Order** | Screen reader users and keyboard-only users cannot navigate the app at all |
| **Fix** | Add `role="button"`, `tabIndex={0}`, and `onKeyDown` handlers to interactive div elements |
| **Status** | ✅ FIXED (core interactive elements) |

### RL4-16: No `aria-label` on Interactive Elements [ACCESSIBILITY — Layer 12]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | Buttons like "✕" (close/remove) have no accessible labels |
| **First Principles** | Screen readers cannot convey meaning of icon-only buttons without labels |
| **Fix** | Add `aria-label` attributes to icon-only buttons and key interactive elements |
| **Status** | ✅ FIXED (critical elements) |

### RL4-17: `MAX_UPLOAD_SIZE_MB` Not Communicated to Frontend [EXPERIENCE — Layer 14]
| Dimension | Analysis |
|-----------|----------|
| **Root Cause** | Backend has a configurable `MAX_UPLOAD_SIZE_MB` but the frontend has no way to know the limit. The health endpoint doesn't expose it |
| **First Principles** | System limits should be communicated, not discovered through failure |
| **Second-Order** | User uploads a 3GB video, waits for network transfer, then gets a 413 error |
| **Fix** | Add `max_upload_size_mb` to health endpoint response |
| **Status** | ✅ FIXED |

---

## 📊 RL4 Summary

| Metric | Count |
|--------|-------|
| **Issues Found** | 17 |
| **Fixed** | 15 |
| **Documented** | 2 |

### Cumulative Ralph Loop Stats

| Loop | Issues | Fixed | Documented | Focus |
|------|--------|-------|------------|-------|
| RL1 | 13 | 13 | 0 | Code-level bugs |
| RL2 | 17 | 12 | 7 | Second-order effects |
| RL3 | 15 | 9 | 6 | Emergent fix interactions |
| RL4 | 17 | 15 | 2 | 14-layer architecture blind spots |
| **Total** | **62** | **49** | **15** |  |

### Layers Exercised

| Layer | Issues | Description |
|-------|--------|-------------|
| 3: Failure Map | 1 | Error boundary |
| 6: Validation | 1 | Input validation |
| 8: Persistence | 1 | Compare list session storage |
| 9: Security | 5 | Path traversal, secrets, headers, Docker |
| 10: Resilience | 2 | Docker healthcheck, error boundary |
| 12: Accessibility | 2 | Keyboard nav, ARIA labels |
| 13: Evolution | 3 | Dead code, temp files |
| 14: Experience | 2 | Upload limits, render guards |

---

## 🔐 Security Recommendations (Immediate Actions)

1. **ROTATE THE HF_TOKEN** — The token `hf_REDACTED` should be considered compromised. Generate a new one at https://huggingface.co/settings/tokens
2. **Delete `temp_api.json` files** — May contain API response data
3. **Delete `nul` file** — Windows artifact
4. **Check git history** — Ensure no secrets were ever committed to version control
