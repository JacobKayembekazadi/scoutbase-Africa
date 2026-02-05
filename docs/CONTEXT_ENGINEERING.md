# Context Engineering Strategy

> A comprehensive guide to maximizing AI assistant effectiveness through strategic context management.

---

## Table of Contents

1. [What is Context Engineering?](#what-is-context-engineering)
2. [The Context Hierarchy](#the-context-hierarchy)
3. [Context Document Types](#context-document-types)
4. [Loading Strategies](#loading-strategies)
5. [Context Compression Techniques](#context-compression-techniques)
6. [Session Management](#session-management)
7. [Multi-Agent Coordination](#multi-agent-coordination)
8. [Context Templates](#context-templates)
9. [Anti-Patterns](#anti-patterns)
10. [Measuring Effectiveness](#measuring-effectiveness)

---

## What is Context Engineering?

Context engineering is the practice of **strategically designing, organizing, and delivering information to AI assistants** to maximize the quality, relevance, and efficiency of their outputs.

### Why It Matters

| Without Context Engineering | With Context Engineering |
|----------------------------|--------------------------|
| Generic, one-size-fits-all responses | Tailored, project-specific solutions |
| Repeated explanations every session | Persistent knowledge across sessions |
| Inconsistent coding patterns | Enforced conventions and standards |
| Vague, hallucinated details | Grounded, accurate information |
| Wasted tokens on irrelevant context | Efficient, focused context loading |

### Core Principle

> **Context is the most important input to an AI assistant.** A mediocre prompt with excellent context produces better results than an excellent prompt with poor context.

---

## The Context Hierarchy

Context exists in layers, from most persistent to most ephemeral:

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: PROJECT IDENTITY                                   │
│ What is this project? Who is it for? What problem does it   │
│ solve? Core principles and values.                          │
│ Persistence: Permanent | Update: Rarely                     │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: TECHNICAL ARCHITECTURE                             │
│ System design, tech stack, data models, API contracts,      │
│ integration points, deployment topology.                     │
│ Persistence: Long-term | Update: When architecture changes  │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: CONVENTIONS & STANDARDS                            │
│ Coding style, naming conventions, file organization,        │
│ documentation standards, review criteria.                    │
│ Persistence: Long-term | Update: When standards evolve      │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: CURRENT STATE                                      │
│ What's built, what's in progress, known issues, technical   │
│ debt, upcoming priorities.                                   │
│ Persistence: Medium-term | Update: Weekly                   │
├─────────────────────────────────────────────────────────────┤
│ Layer 5: TASK CONTEXT                                       │
│ Specific task requirements, acceptance criteria,            │
│ constraints, relevant code snippets.                         │
│ Persistence: Session | Update: Per task                     │
├─────────────────────────────────────────────────────────────┤
│ Layer 6: CONVERSATION CONTEXT                               │
│ Current discussion, decisions made, code written,           │
│ questions asked, feedback received.                          │
│ Persistence: Ephemeral | Update: Continuous                 │
└─────────────────────────────────────────────────────────────┘
```

### Loading Strategy by Layer

| Layer | When to Load | How to Load |
|-------|--------------|-------------|
| 1. Project Identity | Every session | System prompt or first message |
| 2. Technical Architecture | Most sessions | Reference doc at session start |
| 3. Conventions | When writing code | Inline or as reference |
| 4. Current State | Every session | Updated summary |
| 5. Task Context | Per task | Focused, relevant snippets |
| 6. Conversation | Automatic | Managed by AI memory |

---

## Context Document Types

### 1. Project Context Document (SCOUTBASE_CONTEXT.md)

**Purpose:** Single source of truth for project understanding

**Contents:**
- Project mission and problem statement
- Target users and use cases
- Core principles and values
- High-level architecture
- Key terminology
- Success metrics

**Example Structure:**
```markdown
# PROJECT CONTEXT

## What Is This
[One paragraph explanation]

## The Problem
[Why this project exists]

## First Principles
[Guiding design decisions]

## Key Terminology
| Term | Definition |
|------|------------|
| ... | ... |

## Success Metrics
- Metric 1: [target]
- Metric 2: [target]
```

### 2. Technical Architecture Document (ARCHITECTURE.md)

**Purpose:** System design and technical decisions

**Contents:**
- System architecture diagram
- Tech stack with justifications
- Data models and relationships
- API contracts
- Integration points
- Deployment topology

**Example Structure:**
```markdown
# TECHNICAL ARCHITECTURE

## System Diagram
[ASCII or Mermaid diagram]

## Tech Stack
| Component | Technology | Why |
|-----------|-----------|-----|
| ... | ... | ... |

## Data Models
[Key entities and relationships]

## API Contracts
[Endpoint specifications]

## Deployment
[How and where this runs]
```

### 3. Coding Conventions Document (CONVENTIONS.md)

**Purpose:** Enforce consistency across codebase

**Contents:**
- Language-specific style guides
- Naming conventions
- File organization
- Error handling patterns
- Documentation standards
- Testing requirements

**Example Structure:**
```markdown
# CODING CONVENTIONS

## Python
### Style
- [Rule 1]
- [Rule 2]

### Naming
- Functions: snake_case
- Classes: PascalCase

### Error Handling
- [Pattern]

## TypeScript
### Style
- [Rule 1]
- [Rule 2]

### Components
- [Structure]
```

### 4. Current State Document (CURRENT_STATE.md)

**Purpose:** Snapshot of project status

**Contents:**
- What's working
- What's in progress
- What's planned
- Known issues
- Technical debt
- Recent decisions

**Example Structure:**
```markdown
# CURRENT STATE
Last Updated: [DATE]

## Working
- [x] Feature 1
- [x] Feature 2

## In Progress
- [ ] Feature 3 (70%)
- [ ] Feature 4 (30%)

## Planned
- [ ] Feature 5
- [ ] Feature 6

## Known Issues
- Issue 1: [description]
- Issue 2: [description]

## Technical Debt
- [ ] Debt item 1
- [ ] Debt item 2

## Recent Decisions
- Decision 1: [rationale]
- Decision 2: [rationale]
```

### 5. Task Specification Document

**Purpose:** Define specific work items

**Contents:**
- Objective
- Acceptance criteria
- Constraints
- Not in scope
- Relevant context
- Questions

**Example Structure:**
```markdown
# TASK: [Name]

## Objective
[What needs to be accomplished]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Constraints
- Constraint 1
- Constraint 2

## Not In Scope
- Out of scope 1
- Out of scope 2

## Relevant Context
[Code snippets, file references, etc.]

## Questions
- Question 1?
- Question 2?
```

---

## Loading Strategies

### Strategy 1: Layered Loading

Load context in order of importance, stopping when token limits approach:

```
1. Always load: Project identity (Layer 1)
2. Usually load: Architecture + Current State (Layers 2, 4)
3. Task-dependent: Conventions + Task Context (Layers 3, 5)
4. As needed: Specific code files
```

### Strategy 2: Just-In-Time Loading

Load minimal context initially, fetch more as needed:

```
Initial: Project summary + Task specification
On demand: "Read the api.ts file to understand existing patterns"
On demand: "What conventions do we use for error handling?"
```

### Strategy 3: Role-Based Loading

Load context based on the role the AI is playing:

| Role | Context to Load |
|------|-----------------|
| Architect | Full architecture, API contracts, data models |
| Implementer | Conventions, relevant code files, task spec |
| Reviewer | Conventions, quality standards, code under review |
| Debugger | Error logs, relevant code paths, recent changes |
| Documenter | Existing docs, feature specs, API contracts |

### Strategy 4: Diff-Based Loading

For modifications, load only what's changing:

```
Instead of: Full file (500 lines)
Load: Relevant function + 10 lines context
Plus: Type definitions it depends on
Plus: Similar functions for pattern matching
```

---

## Context Compression Techniques

### 1. Summarization

Convert detailed documentation into condensed summaries:

**Before (verbose):**
```markdown
The ScoutBase Africa Vision OS platform uses YOLO v11 for object
detection, which identifies all persons in each video frame. This
is followed by ByteTrack multi-object tracking, which assigns
persistent track IDs to each detected person across all frames...
```

**After (compressed):**
```markdown
Vision Pipeline: YOLO v11 (detection) → ByteTrack (tracking) →
Metrics extraction → AI report generation
```

### 2. Structured Formatting

Use tables and lists instead of prose:

**Before:**
```markdown
The API has several endpoints. The /process endpoint accepts video
uploads and starts processing. The /status endpoint checks job
status. The /results endpoint returns tracking data...
```

**After:**
```markdown
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /process | POST | Upload + start processing |
| /status/{id} | GET | Check job status |
| /results/{id} | GET | Get tracking data |
```

### 3. Code Pattern Extraction

Instead of full files, extract patterns:

**Before:** Full 500-line server.py

**After:**
```python
# Endpoint pattern (server.py)
@app.post("/endpoint")
async def endpoint_name(request: RequestModel):
    if error_condition:
        raise HTTPException(400, "message")
    result = process(request)
    return ResponseModel(**result)
```

### 4. Reference Linking

Use pointers instead of inline content:

```markdown
## Authentication
See: server.py:678-720 (auth middleware)
See: web/src/lib/auth.ts (frontend auth)
Pattern: JWT tokens in Authorization header
```

### 5. Semantic Chunking

Group related information together:

```markdown
## Video Processing Module

Files: process_match.py, server.py:/process endpoint
Models: ProcessingJob, ProcessingRequest, ProcessingResults
Flow: Upload → Queue → YOLO → ByteTrack → Metrics → Store
Status: Working, tested with 90-min matches
```

---

## Session Management

> **⚠️ CRITICAL RULE**: Every session MUST end with updating `CURRENT_STATE.md`.
> This is non-negotiable. See the Session End section below.

### Session Initialization Template

```markdown
# Session Start

## Project
ScoutBase Africa Vision OS - AI-powered player tracking

## Today's Focus
[Specific task or feature]

## Key Context
- Tech: Python/FastAPI backend, Next.js frontend
- Current: SAM3 integration 70% complete
- Constraint: Must work without GPU

## Files Likely Needed
- sam3/processor.py (main work)
- server.py (endpoint integration)
- web/src/lib/api.ts (frontend types)

## Ready to Begin
[Specific first action]
```

### Session Continuation Template

```markdown
# Continuing Previous Session

## Last Session Summary
- Completed: types.py, config.py, model_loader.py
- In progress: processor.py (segment_frame done)
- Decision: Using SAM2 models as fallback

## This Session Goals
1. Complete processor.py (track_video, segment_teams)
2. Add server.py endpoints
3. Update frontend types

## Pickup Point
Continue from processor.py line 180, track_video method
```

### Session Handoff Template

```markdown
# Session Handoff

## Completed This Session
- [x] Added SAM3 segment endpoint
- [x] Added SAM3 teams endpoint
- [x] Updated frontend types

## Incomplete
- [ ] SAM3 enhance endpoint (started, 50%)
- [ ] Frontend API functions

## Decisions Made
1. RLE encoding for masks (smaller payload)
2. Lazy model loading (memory efficiency)
3. 50ms target per frame (acceptable latency)

## Blockers
None

## Next Session Should
1. Complete enhance endpoint
2. Add frontend API functions
3. Test end-to-end with real video

## Context for Next Session
Key file: sam3/processor.py:enhance_tracks method
Pattern: Follow existing /results/{job_id}/tracks endpoint
```

---

## Multi-Agent Coordination

When using multiple AI agents (or multiple sessions), coordinate context:

### Shared Context Repository

```
context/
├── PROJECT.md           # Shared: Project identity
├── ARCHITECTURE.md      # Shared: Technical design
├── CONVENTIONS.md       # Shared: Coding standards
├── CURRENT_STATE.md     # Shared: Updated frequently
├── agents/
│   ├── architect.md     # Agent-specific context
│   ├── implementer.md   # Agent-specific context
│   └── reviewer.md      # Agent-specific context
└── tasks/
    ├── task-001.md      # Task-specific context
    ├── task-002.md      # Task-specific context
    └── task-003.md      # Task-specific context
```

### Agent Communication Protocol

```markdown
## Agent Handoff Format

### From: Architect Agent
### To: Implementer Agent
### Task: SAM3 Integration

## Design Decisions
- Module structure: sam3/{__init__, config, loader, processor, types}
- Lazy loading pattern for memory efficiency
- RLE encoding for mask serialization

## API Contract
POST /sam3/segment
Request: {job_id, frame_number, prompt, confidence_threshold}
Response: {success, objects[], processing_time_ms}

## Implementation Notes
- Follow existing endpoint patterns in server.py
- Use Pydantic models matching these specs
- Add to existing error handling middleware

## Constraints
- Must work without GPU (CPU fallback)
- Model loads only on first request
- Target <100ms per frame on GPU
```

### Conflict Resolution

When agents produce conflicting outputs:

1. **Identify the conflict** - What specifically differs?
2. **Check constraints** - Which approach satisfies requirements?
3. **Consult conventions** - Which matches existing patterns?
4. **Escalate to human** - If still unclear, human decides

---

## Context Templates

### Template: New Feature

```markdown
# Feature: [Name]

## Overview
[One paragraph description]

## User Story
As a [user type], I want to [action] so that [benefit].

## Technical Approach
[High-level implementation strategy]

## Files to Create/Modify
| File | Action | Description |
|------|--------|-------------|
| ... | Create/Modify | ... |

## Data Models
[New types or schema changes]

## API Endpoints
[New or modified endpoints]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Non-Functional Requirements
- Performance: [target]
- Security: [considerations]

## Dependencies
- Depends on: [other features/services]
- Blocks: [features waiting on this]

## Open Questions
- Question 1?
- Question 2?
```

### Template: Bug Fix

```markdown
# Bug: [Title]

## Symptoms
[What the user experiences]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Reproduction Steps
1. Step 1
2. Step 2
3. Step 3

## Error Output
```
[Error message or stack trace]
```

## Hypothesis
[Suspected root cause]

## Investigation Plan
1. Check [area 1]
2. Check [area 2]
3. Check [area 3]

## Relevant Files
- file1.py:123 (suspected location)
- file2.py:456 (related code)

## Fix Approach
[Proposed solution]

## Testing
[How to verify the fix]
```

### Template: Code Review

```markdown
# Review: [PR/Change Title]

## Summary
[What this change does]

## Files Changed
| File | Lines | Type |
|------|-------|------|
| ... | +X/-Y | New/Modified |

## Review Checklist

### Correctness
- [ ] Logic is correct
- [ ] Edge cases handled
- [ ] Error handling appropriate

### Security
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] No injection vulnerabilities

### Performance
- [ ] No obvious bottlenecks
- [ ] Async where appropriate
- [ ] Memory usage reasonable

### Style
- [ ] Follows conventions
- [ ] Types complete
- [ ] Comments appropriate

## Feedback

### Critical
[Must fix before merge]

### Suggestions
[Consider changing]

### Questions
[Clarification needed]

## Verdict
[ ] Approve
[ ] Request Changes
[ ] Need Discussion
```

---

## Anti-Patterns

### 1. Context Overload

**Problem:** Loading entire codebase into context
**Symptoms:** Slow responses, irrelevant suggestions, token limits
**Solution:** Load only relevant files, use summaries

### 2. Context Starvation

**Problem:** Providing too little context
**Symptoms:** Generic responses, wrong patterns, hallucinations
**Solution:** Include project identity, conventions, relevant examples

### 3. Context Rot

**Problem:** Outdated context documents
**Symptoms:** Suggestions contradict current state, obsolete patterns
**Solution:** Regular context document updates, date stamps

### 4. Context Fragmentation

**Problem:** Information scattered across many documents
**Symptoms:** Inconsistent responses, repeated questions
**Solution:** Consolidate related information, clear hierarchy

### 5. Context Duplication

**Problem:** Same information in multiple places
**Symptoms:** Contradictions, maintenance burden
**Solution:** Single source of truth, references over copies

### 6. Implicit Context

**Problem:** Assuming AI knows project-specific details
**Symptoms:** Wrong assumptions, missed constraints
**Solution:** Make everything explicit, no tribal knowledge

---

## Measuring Effectiveness

### Context Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| First-response accuracy | >80% | Correct without clarification |
| Pattern adherence | >90% | Matches existing codebase style |
| Hallucination rate | <5% | Fabricated facts or code |
| Context utilization | >70% | Loaded context actually used |

### Context Efficiency Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Tokens per task | Minimize | Context tokens / useful output |
| Load time | <30s | Time to load and parse context |
| Update frequency | Weekly | How often docs need refresh |
| Reuse rate | >70% | Same docs used across sessions |

### Tracking Template

```markdown
# Context Effectiveness Log

## Session: [Date]

### Context Loaded
- PROJECT.md (2,000 tokens)
- ARCHITECTURE.md (3,000 tokens)
- server.py excerpt (500 tokens)
Total: 5,500 tokens

### Task Completed
Implemented SAM3 segment endpoint

### Quality Assessment
- First response correct: Yes
- Pattern adherence: 95%
- Clarifications needed: 1
- Hallucinations: 0

### Context Notes
- Needed to load types.ts mid-session
- Could have pre-loaded conventions
- Architecture doc section on API was key

### Improvements for Next Time
- Pre-load API conventions
- Include endpoint pattern template
```

---

## Quick Reference

### Session Start Checklist

```
[ ] READ CURRENT_STATE.md first (mandatory)
[ ] Load project identity document (SCOUTBASE_CONTEXT.md)
[ ] Check "What's In Progress" for active tasks
[ ] Check "Known Issues" for blockers
[ ] Define today's task clearly
[ ] Set constraints explicitly
[ ] Identify relevant files
[ ] Enter appropriate role
[ ] Request plan before implementation
```

### Session End Checklist (MANDATORY)

```
[ ] Summarize what was accomplished
[ ] UPDATE CURRENT_STATE.md ← NON-NEGOTIABLE
    [ ] Update "Last Updated" date
    [ ] Update "Updated By" with your model name
    [ ] Add entry to "Recent Changes" section
    [ ] Update status tables if changed
    [ ] Update "Known Issues" if discovered any
    [ ] Update "Technical Debt" if added/resolved any
[ ] List any incomplete items for next session
[ ] Note any decisions made
```

> **WARNING**: Ending a session without updating `CURRENT_STATE.md` is a
> violation of project protocol. ALWAYS update before ending.

### Context Loading Priority

```
1. ALWAYS: Project identity, current state
2. USUALLY: Architecture, conventions
3. TASK-SPECIFIC: Relevant code, task spec
4. AS-NEEDED: Additional files on request
```

### Compression Checklist

```
[ ] Tables over prose
[ ] Patterns over full files
[ ] Summaries over details
[ ] References over copies
[ ] Examples over explanations
```

---

## Conclusion

Context engineering is the highest-leverage skill for AI-assisted development. A well-designed context system:

- **Reduces waste** - No tokens spent on irrelevant information
- **Increases accuracy** - AI has the information it needs
- **Ensures consistency** - Same patterns across all sessions
- **Enables scaling** - Multiple agents, multiple sessions, same quality

Invest in your context documents. They are as important as your codebase.

---

*Context Engineering Strategy v1.0 - ScoutBase Africa Vision OS*
