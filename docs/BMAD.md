# BMAD: Breakthrough Method for Agile AI-Driven Development

> A methodology for building software products with AI assistants as collaborative partners.

---

## ⚠️ CRITICAL: State Management Protocol ⚠️

> **EVERY AI AGENT MUST UPDATE `CURRENT_STATE.md` AFTER EVERY SESSION.**

This is the **#1 rule** of BMAD. Without state tracking, the methodology fails.

### Required Actions:
1. **START of session**: Read `CURRENT_STATE.md`
2. **END of session**: Update `CURRENT_STATE.md` with changes made
3. **NO EXCEPTIONS**: Even for small changes, document them

### What to Update:
- "Last Updated" date and "Updated By" model name
- "Recent Changes" section with detailed entry
- Status tables if component status changed
- "Known Issues" if bugs discovered
- "Technical Debt" if debt added/resolved
- "What's In Progress" if task status changed

**See `CURRENT_STATE.md` for exact format and instructions.**

---

## Overview

BMAD is a development methodology designed for the age of AI-assisted software engineering. It treats AI assistants not as tools to be prompted, but as collaborative partners with specific roles, responsibilities, and constraints. The methodology emphasizes **context engineering**, **role specialization**, and **iterative refinement** to maximize the quality and velocity of AI-assisted development.

This document defines how ScoutBase Africa Vision OS is developed using BMAD principles.

---

## Core Principles

### 1. Context is Everything

AI assistants are only as good as the context they receive. BMAD prioritizes:

- **Rich project documentation** that can be loaded into any AI context
- **Explicit mental models** that capture domain knowledge
- **Architectural decision records** that explain the "why"
- **Terminology glossaries** that prevent ambiguity

### 2. Roles, Not Prompts

Instead of ad-hoc prompts, BMAD defines **persistent roles** for AI assistants:

| Role | Responsibility | Context Required |
|------|----------------|------------------|
| **Architect** | System design, API contracts, data models | Full project context + technical constraints |
| **Implementer** | Code generation, feature building | Specific module context + coding conventions |
| **Reviewer** | Code review, security audit, best practices | Codebase + quality standards |
| **Documenter** | README, API docs, comments | Feature specs + existing docs |
| **Debugger** | Error analysis, root cause investigation | Error logs + relevant code paths |
| **Planner** | Task breakdown, estimation, prioritization | Product requirements + current state |

### 3. Iterative Refinement Over One-Shot Generation

BMAD rejects the "generate everything at once" approach. Instead:

1. **Plan** → AI proposes approach, human validates
2. **Scaffold** → AI generates structure, human reviews
3. **Implement** → AI fills in details, human tests
4. **Refine** → AI improves based on feedback
5. **Document** → AI captures decisions and patterns

### 4. Human-in-the-Loop Decision Points

Critical decisions require human judgment:

- Architectural choices (frameworks, patterns)
- Security-sensitive code paths
- Business logic validation
- Production deployment approval
- Data model changes

### 5. Explicit Constraints

AI assistants work best with clear boundaries:

```markdown
## Constraints for this session

- DO: Use TypeScript strict mode
- DO: Follow existing patterns in /lib/api.ts
- DO NOT: Modify database schema without explicit approval
- DO NOT: Add new dependencies without justification
- PREFER: Editing existing files over creating new ones
- PREFER: Simple solutions over clever abstractions
```

---

## BMAD Workflow

### Phase 1: Context Loading

Before any development session, load these context documents:

```
Required Context Documents:
├── SCOUTBASE_CONTEXT.md      # Full project understanding
├── ARCHITECTURE.md           # Technical architecture
├── CODING_CONVENTIONS.md     # Style and patterns
└── CURRENT_STATE.md          # What's built, what's next
```

**Context Loading Prompt:**
```
I'm working on ScoutBase Africa Vision OS. Please read and internalize:

1. The project context (SCOUTBASE_CONTEXT.md)
2. The technical architecture (ARCHITECTURE.md)
3. Current task: [SPECIFIC TASK]

Confirm your understanding by summarizing:
- What ScoutBase does
- The current technical stack
- What you'll be working on today
```

### Phase 2: Task Definition

Every task needs explicit definition:

```markdown
## Task: Add SAM3 Text-Prompted Segmentation

### Objective
Enable users to segment video frames using natural language prompts
like "players in blue jerseys" or "goalkeeper".

### Acceptance Criteria
- [ ] New `/sam3/segment` endpoint accepts text prompts
- [ ] Returns segmentation masks with confidence scores
- [ ] Integrates with existing job system
- [ ] TypeScript types match Python Pydantic models

### Constraints
- Must work without GPU (CPU fallback)
- Model loads lazily (not on server startup)
- Follow existing patterns in server.py

### Not In Scope
- Real-time video streaming
- Model fine-tuning
- UI components (separate task)
```

### Phase 3: Planning Mode

Before writing code, AI enters "planning mode":

```
Enter planning mode for: Add SAM3 Text-Prompted Segmentation

1. Analyze existing codebase patterns
2. Identify files to modify vs create
3. Propose implementation approach
4. List potential risks and mitigations
5. Present plan for human approval

Do NOT write code until plan is approved.
```

**Planning Output Format:**
```markdown
## Implementation Plan: SAM3 Integration

### Files to Create
- sam3/__init__.py (module exports)
- sam3/config.py (environment config)
- sam3/model_loader.py (lazy loading)
- sam3/processor.py (core logic)
- sam3/types.py (Pydantic models)

### Files to Modify
- server.py (add endpoints, ~50 lines)
- requirements.txt (add 3 dependencies)
- web/src/lib/api.ts (add API functions)
- web/src/lib/types.ts (add TypeScript types)

### Approach
1. Create sam3 module with lazy model loading
2. Add SAM3 endpoints following existing patterns
3. Frontend types mirror backend Pydantic models
4. Test with sample frame before video integration

### Risks
- HuggingFace auth may fail → fallback to unavailable status
- GPU memory exhaustion → add memory checks
- Model not released yet → use SAM2 as fallback

### Questions for Human
1. Should SAM3 processing be async (background job)?
2. Preferred model variant (base/large/huge)?
```

### Phase 4: Implementation

After plan approval, implement incrementally:

```
Plan approved. Begin implementation.

Order of operations:
1. Create types.py (data contracts first)
2. Create config.py (environment handling)
3. Create model_loader.py (lazy loading)
4. Create processor.py (core logic)
5. Update server.py (endpoints)
6. Update frontend types and API

After each file, pause for review before continuing.
```

### Phase 5: Review and Refinement

Self-review checklist:

```markdown
## Code Review Checklist

### Correctness
- [ ] Handles all edge cases
- [ ] Error messages are helpful
- [ ] Async operations properly awaited

### Security
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] No injection vulnerabilities

### Performance
- [ ] No N+1 queries
- [ ] Large operations are async
- [ ] Memory-efficient for video processing

### Maintainability
- [ ] Follows existing patterns
- [ ] Type hints complete
- [ ] Comments explain "why", not "what"

### Testing
- [ ] Can be tested manually
- [ ] Error paths tested
- [ ] Edge cases documented
```

### Phase 6: Documentation

Every feature ships with documentation:

```markdown
## Documentation Requirements

- [ ] README updated if public API changed
- [ ] Type definitions match implementation
- [ ] API endpoints documented with examples
- [ ] Environment variables documented
- [ ] Error codes documented
```

---

## Role-Specific Prompts

### Architect Role

```
You are the ScoutBase system architect. Your role:

1. Design APIs that are consistent with existing endpoints
2. Propose data models that fit the 7-layer architecture
3. Consider scalability (1000s of videos processed daily)
4. Balance complexity vs. maintainability
5. Document architectural decisions

You do NOT write implementation code. You produce:
- API specifications
- Data model diagrams
- Architecture decision records
- Integration points
```

### Implementer Role

```
You are a ScoutBase implementer. Your role:

1. Write production-quality code following conventions
2. Match existing patterns in the codebase
3. Handle errors gracefully with helpful messages
4. Add type hints and minimal necessary comments
5. Create small, focused commits

You ALWAYS:
- Read existing code before writing new code
- Ask clarifying questions before making assumptions
- Test your code mentally before proposing it
- Prefer editing existing files over creating new ones
```

### Reviewer Role

```
You are a ScoutBase code reviewer. Your role:

1. Identify bugs, security issues, and performance problems
2. Suggest improvements without being pedantic
3. Check for consistency with existing patterns
4. Verify error handling is comprehensive
5. Ensure types are correct and complete

You provide feedback in this format:
- CRITICAL: Must fix before merge
- SUGGESTION: Consider changing
- NITPICK: Minor style preference
- QUESTION: Clarification needed
```

### Debugger Role

```
You are a ScoutBase debugger. Your role:

1. Analyze error messages and stack traces
2. Form hypotheses about root causes
3. Suggest targeted investigation steps
4. Propose fixes with minimal side effects
5. Identify patterns that might cause similar bugs

When debugging:
- Start with the error message
- Work backwards through the call stack
- Check recent changes first
- Consider environment differences
- Look for similar past issues
```

---

## Context Documents Template

### CURRENT_STATE.md

```markdown
# Current Project State

Last Updated: [DATE]

## What's Working
- [ ] Video upload and processing (YOLO + ByteTrack)
- [ ] Player tracking with persistent IDs
- [ ] Web dashboard with job management
- [ ] Track-to-player assignment

## What's In Progress
- [ ] SAM3 integration (text-prompted segmentation)
- [ ] Team differentiation by jersey color

## What's Next
- [ ] Real-time processing feedback
- [ ] Player profile pages
- [ ] Shortlist management

## Known Issues
- CPU processing is slow (~60 min for 90 min match)
- ByteTrack occasionally loses tracks during occlusion

## Technical Debt
- In-memory job storage (needs Redis/DB)
- No authentication yet
- Missing comprehensive error handling
```

### CODING_CONVENTIONS.md

```markdown
# Coding Conventions

## Python (Backend)

### Style
- Type hints on all function signatures
- Dataclasses or Pydantic for data structures
- Async for I/O operations
- f-strings for string formatting

### Naming
- snake_case for functions and variables
- PascalCase for classes
- SCREAMING_SNAKE_CASE for constants
- Descriptive names over abbreviations

### Structure
- One class per file for large classes
- Group related functions in modules
- Keep files under 500 lines

### Error Handling
- Raise HTTPException for API errors
- Log errors with context
- Return helpful error messages

## TypeScript (Frontend)

### Style
- Strict mode enabled
- Explicit return types on functions
- Interface over type for objects
- Const assertions where appropriate

### Naming
- camelCase for functions and variables
- PascalCase for components and types
- Descriptive prop names

### Structure
- One component per file
- Colocate types with components
- Separate API functions in lib/api.ts
```

---

## Anti-Patterns to Avoid

### 1. Context Dumping
**Wrong:** Paste entire codebase into context
**Right:** Load relevant files for current task

### 2. Vague Prompts
**Wrong:** "Make it better"
**Right:** "Add error handling for the case where video file is corrupted"

### 3. Skipping Planning
**Wrong:** "Write the SAM3 integration"
**Right:** "Enter planning mode for SAM3 integration. Analyze existing patterns first."

### 4. Ignoring Constraints
**Wrong:** Let AI choose any approach
**Right:** "Use the existing patterns in server.py. Do not create new frameworks."

### 5. One-Shot Everything
**Wrong:** "Generate all files for SAM3 module"
**Right:** "Start with types.py. We'll review before continuing."

---

## Session Management

### Starting a Session

```markdown
## Session Start Checklist

1. [ ] Load project context documents
2. [ ] State current task clearly
3. [ ] Define constraints and acceptance criteria
4. [ ] Enter appropriate role (architect/implementer/etc.)
5. [ ] Request planning before implementation
```

### Ending a Session

```markdown
## Session End Checklist

1. [ ] Summarize what was accomplished
2. [ ] List any incomplete items
3. [ ] Document decisions made
4. [ ] **UPDATE CURRENT_STATE.md** ← MANDATORY, NON-NEGOTIABLE
5. [ ] Note any context for next session
```

> **⚠️ WARNING**: Do NOT end a session without updating `CURRENT_STATE.md`.
> This is the single most important action for project continuity.

**CURRENT_STATE.md Update Required**:
```markdown
### YYYY-MM-DD - [Brief Description]
**By**: [Your Model Name]

**Added**:
- [List new files, features, or capabilities]

**Modified**:
- [List changed files with brief description]

**Removed**:
- [List deleted files or removed features]

**Files Changed**: [Total count]
```

### Handoff Between Sessions

```markdown
## Session Handoff

### Previous Session
- Completed: SAM3 types.py, config.py, model_loader.py
- In Progress: processor.py (segment_frame method done)
- Blocked: None

### This Session
- Continue: processor.py (track_video, segment_teams)
- Then: server.py endpoint integration
- Context Needed: Existing endpoint patterns in server.py

### Key Decisions Made
- Using SAM2 models as SAM3 fallback
- Lazy loading to save memory
- RLE encoding for masks
```

---

## Measuring BMAD Effectiveness

### Quality Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| First-time correctness | >80% | Code works without major revision |
| Pattern consistency | >90% | Matches existing codebase style |
| Documentation completeness | 100% | All public APIs documented |
| Type coverage | 100% | No `any` types, all functions typed |

### Velocity Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Planning time | <15 min | Time from task start to plan approval |
| Implementation time | Variable | Depends on complexity |
| Review cycles | <2 | Number of revision rounds needed |

### Context Efficiency

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Context reuse | >70% | Same context docs used across sessions |
| Relevant context | >90% | Loaded context actually used |
| Context maintenance | Weekly | Frequency of context doc updates |

---

## Conclusion

BMAD transforms AI-assisted development from ad-hoc prompting into a structured methodology. By investing in context engineering, role specialization, and iterative refinement, teams can achieve higher quality output with greater velocity.

The key insight: **AI assistants are collaborators, not magic wands.** They need context, constraints, and clear roles—just like human team members.

---

*BMAD v1.0 - Adapted for ScoutBase Africa Vision OS*
