---
name: kb-output
description: Render knowledge base content as a Marp slideshow or matplotlib chart. Accepts a question (researches the wiki) or an existing outputs/ file path. Usage: /kb-output --slides <question|file> or /kb-output --chart <question|file>
trigger: /kb-output
---

# KB Output

Render wiki content as a Marp slideshow or matplotlib chart. Supports two format flags (`--slides`, `--chart`) and two content sources (a question or an existing output file).

## Steps

### 1. Check KB Path

```bash
[ -f ".kb/manifest.json" ] || { echo "Not inside a knowledge base."; exit 1; }
```

**If the output is "Not inside a knowledge base." — stop immediately. Do not proceed to any further steps. Reply only with: "Not inside a knowledge base."**

Otherwise, set `KB_PATH` = `$PWD` for all subsequent steps.

### 2. Parse Arguments

The invocation format is: `/kb-output --{format} {source}`

**Extract format flag:**
- `--slides` → set `FORMAT` = `slides`
- `--chart` → set `FORMAT` = `chart`
- If neither flag is present, print: `Usage: /kb-output --slides <question|file> or /kb-output --chart <question|file>` and stop.

**Extract source:**
- Everything after the flag is the `SOURCE` argument.
- If `SOURCE` starts with `outputs/` or ends with `.md` → set `SOURCE_TYPE` = `file`
- Otherwise → set `SOURCE_TYPE` = `question`

### 3. Get Content

#### If SOURCE_TYPE = file

Read the file at `{KB_PATH}/{SOURCE}` using the Read tool.
Extract the body content (below the YAML frontmatter).
Set `CONTENT` = this body text.
Set `TITLE` = the first `#` heading found in the file, or the filename slug if no heading.

#### If SOURCE_TYPE = question

Use index-first wiki navigation to research the question:

1. Read `{KB_PATH}/wiki/index.md`
2. Identify the 3–5 most relevant articles based on the question
3. Read those articles
4. If any article reveals additional relevant concepts or sources via backlinks, read those too (max 8 articles total)
5. Synthesize the content into a structured outline:
   - Title
   - 3–6 sections, each with a heading and 3–5 key points
   - Summary / takeaways
   - List of wiki sources consulted

Set `CONTENT` = this structured outline.
Set `TITLE` = inferred title from the question.

### 4. Generate Output Slug and Path

Generate a `slug` from `TITLE`:
- Lowercase, replace spaces with `-`, strip punctuation
- Max 50 characters

Set `OUTPUT_DATE` to today's date in `YYYY-MM-DD` format.

---

### 5a. Render Slides (if FORMAT = slides)

Generate a complete Marp-formatted markdown file from `CONTENT`.

Rules:
- First slide: title + 1–2 sentence overview
- One concept or section per slide — never combine multiple sections on one slide
- Max 5 bullet points per slide
- Code blocks get their own dedicated slide
- Last slide always cites wiki sources used
- No walls of text — if a point needs more than one line, split it into sub-bullets

Write to `{KB_PATH}/outputs/{OUTPUT_DATE}-{slug}-slides.md`:

```markdown
---
marp: true
theme: default
paginate: true
---

# {TITLE}

{1–2 sentence overview}

---

## {Section 1 heading}

- {Point}
- {Point}
- {Point}

---

## {Section N heading}

...

---

## Summary

- {Takeaway 1}
- {Takeaway 2}
- {Takeaway 3}

---

*Sources: [[concepts/X]], [[sources/Y]], ...*
```

Set `OUTPUT_FILE` = `outputs/{OUTPUT_DATE}-{slug}-slides.md`

---

### 5b. Render Chart (if FORMAT = chart)

**Step 5b-1: Choose chart type**

Based on `CONTENT`, select the most appropriate chart:

| Content type | Chart type |
|---|---|
| Concept relationships, backlinks, or a network of ideas | NetworkX graph (`networkx` + `matplotlib`) |
| Chronological data, timelines, evolution of a field | Horizontal bar timeline or event plot |
| Comparisons: numbers, benchmarks, sizes, rankings | Bar chart or scatter plot |
| Proportions, distributions, or category breakdowns | Pie chart or histogram |

**Step 5b-2: Extract data**

From `CONTENT`, extract the specific data points, labels, relationships, or values the chart will visualize. Be explicit — hardcode all data into the script (no file reads inside the script).

**Step 5b-3: Write Python script**

Set `PNG_PATH` = `{KB_PATH}/outputs/{OUTPUT_DATE}-{slug}-chart.png`
Set `TMP_SCRIPT` = `{KB_PATH}/.kb/tmp_chart.py`

Write a complete, self-contained Python script to `TMP_SCRIPT`. The script must:
- Import all needed libraries at the top (`matplotlib`, `networkx`, etc.)
- Define all data inline (hardcoded from wiki content — no external reads)
- Generate the chart with a descriptive title and labeled axes or nodes
- Save to `PNG_PATH` using `plt.savefig('{PNG_PATH}', dpi=150, bbox_inches='tight')`
- Call `plt.close()` at the end

Example structure for a bar chart:
```python
import matplotlib.pyplot as plt

labels = ['GPT-4', 'Claude 3', 'Gemini']
scores = [85.4, 86.1, 84.2]

fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(labels, scores, color='steelblue')
ax.set_title('MMLU Benchmark Scores')
ax.set_ylabel('Score (%)')
ax.set_ylim(80, 90)
plt.tight_layout()
plt.savefig('{PNG_PATH}', dpi=150, bbox_inches='tight')
plt.close()
```

Example structure for a NetworkX concept graph:
```python
import matplotlib.pyplot as plt
import networkx as nx

G = nx.Graph()
G.add_edges_from([
    ('transformers', 'attention'),
    ('transformers', 'positional-encoding'),
    ('attention', 'self-attention'),
    ('RLHF', 'reward-model'),
])

fig, ax = plt.subplots(figsize=(10, 7))
pos = nx.spring_layout(G, seed=42)
nx.draw(G, pos, with_labels=True, node_color='steelblue',
        node_size=2000, font_size=10, font_color='white',
        edge_color='gray', ax=ax)
ax.set_title('Concept Relationships')
plt.tight_layout()
plt.savefig('{PNG_PATH}', dpi=150, bbox_inches='tight')
plt.close()
```

**Step 5b-4: Execute script**

```bash
python3 {TMP_SCRIPT}
```

If the command fails, read the error, fix the script, and retry once.

**Step 5b-5: Clean up**

```bash
rm {TMP_SCRIPT}
```

Set `OUTPUT_FILE` = `outputs/{OUTPUT_DATE}-{slug}-chart.png`

---

### 6. Update Index

Append to `## Outputs` in `{KB_PATH}/wiki/index.md`:

```
- [[outputs/{OUTPUT_DATE}-{slug}-{slides|chart}]] — {one-line description of what was rendered and why}
```

For charts, use the `.png` filename without extension as the link target.
Write the updated index back to disk.

### 7. Commit

```bash
cd {KB_PATH} && git add -A && git commit -m "kb: output '{TITLE}' as {FORMAT}"
```

### 8. Print Confirmation

For slides:
```
Slides saved to: outputs/{OUTPUT_DATE}-{slug}-slides.md
Open in Obsidian with the Marp plugin to preview.
```

For charts:
```
Chart saved to: outputs/{OUTPUT_DATE}-{slug}-chart.png
Open in Obsidian to view.
```
