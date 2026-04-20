---
name: kb-ask
description: Ask a question against your personal knowledge base wiki. Reads the index to navigate relevant articles, synthesizes a grounded answer with citations, and saves the answer to outputs/. Usage: /kb-ask <your question>
trigger: /kb-ask
---

# KB Ask

Answer a question using the knowledge base wiki. Uses `wiki/index.md` as the navigation layer — reads the index first, then pulls only the relevant articles. Does not load the full wiki into context.

## Steps

### 1. Check KB Path

```bash
[ -f ".kb/manifest.json" ] || { echo "Not inside a knowledge base."; exit 1; }
```

**If the output is "Not inside a knowledge base." — stop immediately. Do not proceed to any further steps. Reply only with: "Not inside a knowledge base."**

Otherwise, set `KB_PATH` = `$PWD` for all subsequent steps.

### 2. Read the Index

Run:
```bash
cat {KB_PATH}/wiki/index.md
```

This is your navigation map. It contains one-line summaries of every concept, source, and output in the wiki.

### 3. Identify Relevant Articles

Based on the question, scan the index and select the 3–5 most relevant articles. Selection priority:

- **Concept articles** (`concepts/`) — prefer when the question asks about a topic, mechanism, or idea
- **Source articles** (`sources/`) — prefer when the question asks about a specific paper, author, dataset, or work
- **Output articles** (`outputs/`) — check these first if the question may already have been answered in a prior Q&A session

### 4. Read Relevant Articles

For each selected article, read it:
```bash
cat {KB_PATH}/wiki/{article-path}.md
```

If reading an article reveals additional relevant concepts or sources (via its `## Sources` backlinks or body text), read those too. Read at most 8 articles total to stay within context.

### 5. Synthesize Answer

Write a clear, grounded answer to the question:
- Cite specific wiki articles inline using `[[wiki-link]]` format (e.g. `[[concepts/attention-mechanism]]`)
- If the wiki does not contain enough information to answer fully, say so explicitly — state what is known and what is missing. Do not fabricate.
- Match length to complexity: 1 paragraph for simple questions, structured sections with headings for complex ones.

### 6. Generate Output Slug and Path

Generate a `slug` from the question:
- Take the first 6–8 significant words (skip stop words like "what", "is", "the", "how", "does")
- Lowercase, join with `-`
- Example: "what is the attention mechanism?" → `attention-mechanism`

Set `OUTPUT_DATE` to today's date in `YYYY-MM-DD` format.
Set `OUTPUT_FILE` = `outputs/{OUTPUT_DATE}-{slug}.md`

### 7. Write Output File

Write to `{KB_PATH}/{OUTPUT_FILE}`:

```markdown
---
question: {exact question asked}
answered_at: {current UTC ISO timestamp}
sources_consulted: [{comma-separated list of article paths read, e.g. "concepts/attention.md", "sources/vaswani-2017.md"}]
---

# {Question}

{Synthesized answer with [[wiki-link]] citations inline}

## Sources Consulted
{Bulleted list of all articles read, formatted as [[wiki-links]]}
```

### 8. Update Index

Append to the `## Outputs` section of `{KB_PATH}/wiki/index.md`:

```
- [[{OUTPUT_FILE without .md extension}]] — {one-line summary: the question asked and the core answer in one sentence}
```

Write the updated index back to disk.

### 9. Commit

```bash
cd {KB_PATH} && git add -A && git commit -m "kb: answer '{question truncated to 50 chars}'"
```

### 10. Print Confirmation

```
Answer saved to: {OUTPUT_FILE}
```
