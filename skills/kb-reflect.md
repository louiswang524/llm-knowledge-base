---
name: kb-reflect
description: Scan the wiki for cross-cutting connections, implicit relationships, contradictions, and gaps. Writes new synthesis articles and a reflection report. Triggered automatically after /kb-compile, or run manually.
trigger: /kb-reflect
---

# KB Reflect

Discover non-obvious connections across the wiki and write synthesis articles. Uses a two-stage process: cheap index-scan for discovery, targeted deep-read for synthesis.

## Steps

### 1. Read Config

```bash
cat ~/.claude/kb-config.json
```

Extract `kb_path`. Expand `~` to the actual home directory path.
Set this as `KB_PATH` for all subsequent steps.

### 2. Read Reflect State

```bash
cat {KB_PATH}/.kb/reflect_state.json 2>/dev/null
```

If the file exists, parse `last_reflected_at` (ISO timestamp) and `synthesized_articles` (list of paths).
If the file does not exist, set `last_reflected_at` = null (treat all wiki content as "recently changed").

### 3. Identify Recently Changed Articles

Read `.kb/manifest.json`:

```bash
cat {KB_PATH}/.kb/manifest.json
```

Collect all entries where `compiled_at` is more recent than `last_reflected_at`. Extract their `wiki_articles` paths — these are the "recently changed" articles that will be prioritized in Stage 2.

If `last_reflected_at` is null, all wiki articles are considered recently changed.

Set `RECENT_ARTICLES` = this list of paths.

---

## Stage 1 — Discovery (Index Only)

### 4. Read the Full Index

```bash
cat {KB_PATH}/wiki/index.md
```

Using only the one-line summaries in `## Concepts` and `## Sources`, identify the 3–5 strongest connection candidates. Look for:

| Type | What to look for |
|---|---|
| `cross-cutting` | A theme or idea that appears across multiple unrelated sources/concepts |
| `relationship` | Two concepts that seem deeply related but have no `[[link]]` between them |
| `contradiction` | Two sources or concepts that appear to take opposing positions on the same topic |
| `gap` | A theme strongly implied by multiple entries but with no dedicated concept article |

**Priority rule:** Candidates that involve at least one article from `RECENT_ARTICLES` are ranked higher.

**Deduplication:** Skip any connection whose resulting synthesis article already exists in `synthesized_articles` from reflect_state.

For each candidate, record internally:
```
type: cross-cutting | relationship | contradiction | gap
concepts: [slug-a, slug-b, ...]
hypothesis: one sentence describing the connection
articles_to_read: [full paths to read in Stage 2, prioritizing RECENT_ARTICLES + neighbors]
proposed_slug: kebab-case slug for the synthesis article
proposed_title: human-readable title
```

If fewer than 2 strong candidates are found, print:
```
Nothing strong enough to synthesize yet. Run /kb-reflect again after ingesting more content.
```
And stop.

---

## Stage 2 — Synthesis (Deep Read Per Candidate)

For each candidate from Stage 1, do the following:

### 5. Read Relevant Articles

For each path in the candidate's `articles_to_read`, read the file:
```bash
cat {KB_PATH}/wiki/{article-path}.md
```

If any article references additional concepts or sources via backlinks that seem directly relevant to the hypothesis, read those too. Maximum 8 articles total per candidate.

### 6. Evaluate Synthesis Quality

Before writing, assess: does the evidence from the articles actually support the hypothesis from Stage 1?

- **Strong evidence** (2+ articles directly support the connection) → write synthesis article
- **Weak evidence** (only superficial overlap) → log as "found but not written" in report, skip article creation

### 7. Write Synthesis Article

For candidates with strong evidence, write to `{KB_PATH}/wiki/concepts/{proposed_slug}.md`:

```markdown
---
tags: [{tags from connected concepts, plus "synthesis"}]
type: synthesis
created_by: kb-reflect
created_at: {current UTC ISO timestamp}
---

# {proposed_title}

{3–5 paragraph synthesis. Explain the connection, relationship, contradiction, or gap clearly.
For connections: what do these concepts share, and why does it matter?
For contradictions: what are the opposing positions, what might explain the disagreement?
For gaps: what is the missing concept, and what would an article about it cover?
Write as a standalone reference — the reader hasn't read the source articles.}

## Connected Concepts
{Bulleted list of [[concepts/{slug}]] for each concept this synthesis draws from}

## Sources
{Bulleted list of [[sources/{slug}]] for each source article consulted}
```

### 8. Update Backlinks in Source Articles

For each concept article listed in `## Connected Concepts` of the new synthesis:

Read the article. If it doesn't already have a `## Connected Concepts` or `## See Also` section, add one. Append:
```
- [[concepts/{proposed_slug}]]
```

---

## Finalize

### 9. Write Reflection Report

Set `REPORT_DATE` to today's date in `YYYY-MM-DD` format.
Set `REPORT_FILE` = `outputs/{REPORT_DATE}-kb-reflect-report.md`

Write to `{KB_PATH}/{REPORT_FILE}`:

```markdown
# KB Reflect Report — {REPORT_DATE}

## Synthesis Articles Created
{For each article written:}
- [[concepts/{slug}]] — {one-line description of the connection found}

## Connections Found But Not Written
{For each weak-evidence candidate:}
- {hypothesis} — insufficient evidence (articles consulted: {list})

## Suggested Follow-up Ingestion
{Any concepts or topics referenced in synthesis articles that have no source in the wiki yet.
Format: "- {topic} — mentioned in [[concepts/{synthesis-slug}]] but no source exists"}
```

If no synthesis articles were created and no weak candidates, print:
```
Nothing strong enough to synthesize yet.
```
And stop without writing a report.

### 10. Update wiki/index.md

For each synthesis article created, append under `## Concepts`:
```
- [[concepts/{slug}]] — {one-line description} *(synthesis)*
```

Append the report under `## Outputs`:
```
- [[{REPORT_FILE without .md}]] — reflect report: {N} synthesis articles created
```

Write the updated index back to disk.

### 11. Update Reflect State

Write to `{KB_PATH}/.kb/reflect_state.json`:

```json
{
  "last_reflected_at": "{current UTC ISO timestamp}",
  "synthesized_articles": ["{existing list}" + "{newly created paths}"]
}
```

### 12. Commit

```bash
cd {KB_PATH} && git add -A && git commit -m "kb: reflect — {N} synthesis article(s) created"
```

### 13. Print Summary

```
Reflected on {N} candidates:
  ✓ Created: concepts/{slug-1} — {title}
  ✓ Created: concepts/{slug-2} — {title}
  ✗ Skipped: {hypothesis} (weak evidence)

Suggested ingestion:
  - {topic-1}
  - {topic-2}

Report: {REPORT_FILE}
```
