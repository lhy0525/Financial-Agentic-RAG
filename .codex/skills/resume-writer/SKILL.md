---
name: resume-writer
description: "Use when writing role-targeted resume project experience, interview talking points, or bilingual wording for Financial Agentic RAG / Modular RAG MCP Server; triggers include Chinese resume-writing requests, resume, write resume, project experience, interview project packaging, RAG Engineer, Agent Engineer, Backend Engineer, LLM Application Engineer, Financial AI, and full-stack AI roles."
---

# Resume Writer

Write honest, role-targeted resume project experience for Financial Agentic RAG / Modular RAG MCP Server. Keep the output compact, defensible in interviews, and matched to the user's target role.

## Core Rule

- Do not fabricate production adoption, cloud deployment, authentication, multi-tenant isolation, unsupported model providers, or fake metrics.
- Do not claim capabilities not supported by the project references or codebase.
- If real metrics are missing, label numbers as `suggested metrics` and ask the user to confirm or replace them.
- Prefer specific, defensible engineering decisions over inflated business claims.

## Reference Loading

For new or full project resume generation, read:
- `references/resume_principles.md`
- `references/project_overview.md`

For small requests such as rewriting, shortening, or translating an existing bullet, read only the user-provided text plus `references/resume_principles.md`. Load project references only when factual project details are needed.

Read as needed:
- `references/role_profiles.md` when the user has a target role or wants role packaging.
- `references/project_highlights.md` when selecting technical bullets.
- `references/interview_followups.md` when preparing interview follow-up questions or defense wording.

## Workflow

### Phase 1: Collect User Inputs

Collect only what is needed: target role, business framing, technical emphasis, output format, and real metrics. Ask Chinese users in Chinese by default. If information is incomplete, make reasonable assumptions and clearly mark them as assumptions.

For small requests such as "rewrite this bullet", "shorten", or "translate to English", preserve the requested scope. Do not force a full project section or interview follow-ups unless the user asks for them.

Do not force a long questionnaire. Useful prompts include:
- Target role: RAG Engineer, Agent Engineer, Backend Engineer, LLM Application Engineer, Financial AI, or full-stack AI.
- Business framing: financial research, document intelligence, internal knowledge assistant, compliance/search workflow, or generic platform.
- Technical emphasis: SQL evidence, Agent planning, verification, retrieval, MCP/local platform, backend architecture, or UI/full stack.
- Output format: Chinese, English, bilingual, short bullets, full project section, or interview story.
- Real metrics: document scale, latency, evaluation results, test count, deployment status, or "no real metrics yet".

### Phase 2: Select Highlights

If role-targeting is requested, use `role_profiles.md` to choose 4-6 role-aligned highlights. Then use `project_highlights.md` to extract each highlight's technical point, resume wording direction, quantification angle, and honesty boundary.

Prioritize Financial Agentic RAG identity: financial-domain retrieval, SQL-backed evidence, Agent planning, verification, local MCP/platform details, and modular RAG foundations.

### Phase 3: Generate Resume Content

Adapt the structure to the requested format; use the full structure for full project entries, and smaller scoped output for bullet rewrites, translations, or interview-only requests.

Use the four-part structure from `resume_principles.md`:

`Project Name | Time | Role`

`Background`

`Goal`

`Process` with 4-6 bullets

`Result`

`Technical Stack`

Bullet rules:
- Start with active verbs.
- Combine technical decision, implementation detail, and impact.
- Include module names when they make the claim more concrete.
- Use real metrics, or clearly marked `suggested metrics`.
- Keep bullets concise and interview-defensible.

### Phase 4: Prepare Interview Defense

For full project entries or when the user asks for interview prep, provide 5-8 likely interview follow-up questions. For small rewrite, shortening, translation, or interview-not-needed requests, skip this phase unless requested. Use `interview_followups.md` to select questions that match the chosen highlights, especially around architecture choices, retrieval quality, SQL evidence, Agent planning, verification, local MCP integration, and honesty boundaries.

### Phase 5: Iterate

Ask whether the user wants adjustment toward backend, Agent, financial-domain, shorter wording, English, bilingual wording, or STAR story expansion.

## Output Guardrails

- Check that the project reads as Financial Agentic RAG, not only generic Modular RAG.
- Include SQL evidence, Agent planning, verification, and local platform details when relevant to the target role.
- Do not claim direct LLM SQL generation.
- Clearly mark `suggested metrics` and require user confirmation before treating them as real.
- Ensure the final wording fits the target role and avoids unsupported claims.
