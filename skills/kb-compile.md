---
name: kb-compile
description: Compile all uncompiled raw/ content into the wiki. Writes source summaries, creates/updates concept articles with Obsidian backlinks, and updates the index. Run after /kb-ingest to process new content.
trigger: /kb-compile
---

# KB Compile

Batch process all uncompiled raw files into the wiki. Incremental — only processes files with `status: uncompiled` in the manifest.

## Steps

### 1. Derive KB Path

Invoke `/kb-path` to get `KB_PATH`.

### 2. Read Manifest

Run:
```bash
cat {KB_PATH}/.kb/manifest.json
```

Collect all entries where `status` is `"uncompiled"`. If there are none, print `Nothing to compile.` and stop.

### 3. Read Existing Index

Run:
```bash
cat {KB_PATH}/wiki/index.md
```

Keep this in memory — you will append to it throughout this process.

### 4. Process Each Uncompiled File

For each file at `{RAW_KEY}` with `status: uncompiled`, do the following sub-steps in order.

---

#### 4a. Read the raw file

Read `{KB_PATH}/{RAW_KEY}` using the Read tool.

Parse the YAML frontmatter to get `source`, `ingested_at`, and `type`.
The content below the frontmatter block is the main body.

---

#### 4b. Write source summary

Derive `SOURCE_SLUG` from `{RAW_KEY}`: take the filename portion without extension.
Example: `raw/web/abs-1706-03762.md` → `SOURCE_SLUG` = `abs-1706-03762`

Write to `{KB_PATH}/wiki/sources/{SOURCE_SLUG}.md`:

```markdown
---
source: {value of `source` from raw frontmatter}
ingested_at: {value of `ingested_at` from raw frontmatter}
type: {value of `type` from raw frontmatter}
tags: [{3–8 lowercase tags you assign based on content, comma-separated, e.g. ml, transformers, attention}]
---

# {Title: infer from content, URL, or filename}

## Summary
{2–4 sentence summary of the source's main contribution, argument, or subject matter}

## Key Concepts
{Bulleted list of 3–8 key concepts this source covers, each formatted as [[concepts/{concept-slug}]] — {brief description}}

## Notable Details
{Any specific facts, figures, quotes, findings, or techniques worth preserving verbatim}

## Backlinks
- Source file: [[{RAW_KEY without .md extension}]]
```

---

#### 4c. Create or update concept articles

From the Key Concepts list you wrote in 4b, extract each concept slug (the part inside `[[concepts/{concept-slug}]]`).

For each concept slug:

**If `{KB_PATH}/wiki/concepts/{concept-slug}.md` does NOT exist:**

Create it:
```markdown
---
tags: [{relevant tags from the source}]
---

# {Concept Name (title-case of slug, e.g. attention-mechanism → Attention Mechanism)}

{2–4 paragraph article explaining this concept clearly. Write it as a standalone reference: define the concept, explain why it matters, describe how it works, and note any important variants or related ideas. Assume the reader knows the field but is encountering this concept for the first time.}

## Sources
- [[sources/{SOURCE_SLUG}]]
```

**If `{KB_PATH}/wiki/concepts/{concept-slug}.md` DOES exist:**

Read it. Then update it:
1. Add any new information from the current source not already covered in the article body
2. Append `- [[sources/{SOURCE_SLUG}]]` to the `## Sources` section if not already present

---

#### 4d. Update wiki/index.md

For each new concept article created in 4c (skip if the concept entry already exists in the index):

Append under `## Concepts`:
```
- [[concepts/{concept-slug}]] — {one-line description of the concept}
```

For the source summary (skip if already in index):

Append under `## Sources`:
```
- [[sources/{SOURCE_SLUG}]] — {one-line description: what this source is and its main contribution}
```

Only add entries not already present. Check by scanning existing index content.

---

#### 4e. Update manifest entry for this file

Update the entry for `{RAW_KEY}` in the in-memory manifest JSON:

```json
"{RAW_KEY}": {
  "status": "compiled",
  "ingested_at": "{original ingested_at}",
  "compiled_at": "{current UTC ISO timestamp}",
  "source": "{original source}",
  "type": "{original type}",
  "wiki_articles": ["sources/{SOURCE_SLUG}.md", "concepts/{slug1}.md", "concepts/{slug2}.md"],
  "tags": ["{tags you assigned in 4b}"]
}
```

---

### 5. Write Updated Files

After processing all uncompiled files:

1. Write the full updated `wiki/index.md` back to disk (with all appended entries)
2. Write the full updated manifest back to `{KB_PATH}/.kb/manifest.json`

### 6. Rebuild Search Index

If `kb_search.py` exists in `{KB_PATH}`, rebuild the search index:

```bash
python3 {KB_PATH}/kb_search.py --rebuild
```

If the file doesn't exist (first run before search tool is installed), skip this step silently.

### 7. Commit Changes

```bash
cd {KB_PATH} && git add -A && git commit -m "kb: compile {N} source(s) into wiki"
```

Where N is the count of files just compiled.

### 8. Run Reflect

Invoke the `/kb-reflect` skill to discover connections across newly compiled content.

### 9. Print Summary

```
Compiled {N} file(s):
  - {RAW_KEY_1} → wiki/sources/{slug1}.md, wiki/concepts/...
  - {RAW_KEY_2} → wiki/sources/{slug2}.md, wiki/concepts/...
```
