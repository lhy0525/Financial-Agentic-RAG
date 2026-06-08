# Resume Writer Skill Refresh Design

## Context

The existing `.codex/skills/resume-writer` skill was written for the earlier Modular RAG MCP Server story. The repository has since evolved into Financial Agentic RAG: a local-first financial question-answering system built on the Modular RAG/MCP foundation, with SQL evidence, prospectus retrieval, deterministic planning, evidence merging, verification, evaluation, and a FastAPI/React local demo platform.

The skill should now help generate resume project experience that reflects the updated project accurately, without overstating unimplemented capabilities.

## Goal

Upgrade `resume-writer` into a stable, reusable skill for producing role-targeted resume content based on the current Financial Agentic RAG project.

The upgraded skill should:

- Preserve the four-part resume writing method: background, goal, process, result.
- Add the current financial Agentic RAG architecture and capabilities.
- Support role-specific emphasis for RAG, Agent, backend, LLM application, financial AI/data, and full-stack AI demo positions.
- Keep `SKILL.md` lean and move detailed project knowledge into reference files.
- Include interview follow-up prompts so generated resume bullets can be defended in interviews.

## Recommended Approach

Use the standard refresh approach:

- Keep the existing skill directory.
- Rewrite `SKILL.md` as a compact workflow and reference navigator.
- Preserve `resume_principles.md` as the writing-style reference, with cleanup only if needed.
- Replace the old all-in-one `project_highlights.md` with a current, structured project highlight library.
- Add focused reference files for project overview, role mapping, and interview follow-ups.

This is preferred over a light patch because the project has changed enough that a single `project_highlights.md` file would become too dense. It is also preferred over adding scripts because resume generation is a judgment-heavy writing task rather than a deterministic transformation.

## Target Structure

```text
.codex/skills/resume-writer/
  SKILL.md
  references/
    resume_principles.md
    project_overview.md
    project_highlights.md
    role_profiles.md
    interview_followups.md
```

## File Responsibilities

### SKILL.md

`SKILL.md` should become the orchestration guide. It should contain:

- Frontmatter with an updated trigger description for Financial Agentic RAG resume generation.
- A short workflow:
  - Load writing principles.
  - Load project overview.
  - Ask for target role, business framing, desired technical emphasis, and output format.
  - Load role profiles and relevant highlights.
  - Generate resume content.
  - Provide interview follow-up questions.
- Rules for when to read each reference file.
- Output constraints: four-part structure, active verbs, concrete ownership, measurable outcomes, no fake claims.

It should not duplicate long project highlight lists.

### references/resume_principles.md

This file should remain the writing-quality reference. It should cover:

- Background, goal, process, result structure.
- Bullet point quality rules.
- Quantification principles.
- Anti-pattern checks.
- Honest packaging boundaries.

The current file can be retained but should be cleaned up if encoding artifacts interfere with use.

### references/project_overview.md

This file should describe the current project in one stable narrative:

- Financial Agentic RAG is local-first financial QA.
- Modular RAG/MCP remains the foundation.
- The system combines SQL evidence, prospectus evidence, planner/orchestrator, merger/verifier, financial evaluation, and local platform UI.
- Main runtime entry points and major source directories.
- Explicit boundary: local demo platform, no login/cloud/multi-tenant claims.

### references/project_highlights.md

This file should become the canonical technical highlight library. Suggested sections:

- Modular RAG/MCP foundation.
- Hybrid Search: Dense + Sparse + RRF + optional rerank.
- Config-driven provider architecture.
- Ingestion pipeline and local-first indexing.
- MCP tools and JSON-RPC stdio server.
- Observability and evaluation.
- Financial question planner.
- Rule-compiled Text-to-SQL evidence path.
- SQL safety and execution.
- EvidencePackage, EvidenceMerger, and FinancialVerifier.
- Prospectus PDF/TXT evidence and upload indexing.
- FastAPI + React local platform.
- Financial evaluation and golden boundary cases.

Each highlight should include:

- Technical point.
- Resume wording direction.
- Quantification angles.
- Honesty boundaries.

### references/role_profiles.md

This file should map target roles to highlight priority and wording style:

- RAG Engineer.
- Agent Engineer.
- Backend Engineer.
- LLM Application Engineer.
- Financial AI / Data Engineer.
- Full-stack AI Demo / AI Product Engineer.

Each profile should include:

- Best 4-6 highlights to select.
- Keywords for ATS and recruiter scanning.
- Resume narrative angle.
- What to downplay.

### references/interview_followups.md

This file should help the agent prepare the user to defend the generated resume content.

It should include likely follow-up questions and answer directions for:

- Why the router lives in the Agent layer instead of the MCP server.
- Why Text-to-SQL uses deterministic compilation instead of direct LLM SQL generation.
- How SQL safety works.
- How `sql_first` and `doc_first` hybrid orchestration work.
- How evidence merging and verification reduce hallucination risk.
- How prospectus upload and indexing report honest readiness states.
- How the local platform differs from a production SaaS deployment.

## Workflow Design

When triggered, the updated skill should:

1. Read `resume_principles.md` and `project_overview.md`.
2. Ask the user for:
   - Target role.
   - Business framing: real domain, financial AI demo, or generic enterprise knowledge-base framing.
   - Preferred technical emphasis.
   - Output format: Chinese, English, bilingual, bullet-only, or full project entry.
3. Read `role_profiles.md` and the relevant sections of `project_highlights.md`.
4. Generate a role-targeted resume entry using the four-part structure.
5. Add a technical stack line.
6. Add 5-8 likely interview follow-up questions from `interview_followups.md`.
7. Mark any suggested metrics as suggested values unless the user supplied real values.

## Honesty Rules

The skill must not claim:

- Cloud deployment, OAuth/JWT, production multi-tenant isolation, or hosted vector databases.
- CLIP or FAISS usage unless added later.
- LLM-generated SQL if the current path is deterministic rule compilation.
- Full native PDF table docstore support unless implemented and verified.
- Business adoption metrics not provided by the user.

Allowed framing:

- Local-first demo platform.
- Configurable provider architecture.
- SQL-first financial evidence path.
- Prospectus PDF/TXT upload and indexing.
- Hybrid search and MCP integration.
- Evidence verification and traceability.

## Acceptance Criteria

The refresh is complete when:

- `SKILL.md` triggers on resume/project-experience requests for the updated Financial Agentic RAG project.
- `SKILL.md` is concise and references the new files instead of embedding all knowledge inline.
- The reference set contains the five target files.
- Financial Agentic RAG highlights are represented accurately.
- Role-specific generation is supported.
- Interview follow-up preparation is included.
- No reference file claims unimplemented production capabilities.

## Implementation Scope

This design only covers updating `.codex/skills/resume-writer`.

It does not require changing application source code, tests, frontend, runtime config, or other project skills.

