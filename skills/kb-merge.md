---
name: kb-merge
description: Merge duplicate or related concept articles. Accepts an explicit pair (/kb-merge slug-a slug-b) or runs auto-detection from wiki duplicates. Synthesizes a clean merged article, updates all backlinks, and archives the absorbed article.
trigger: /kb-merge
---

# KB Merge

Merge two concept articles into one. Synthesizes content, updates all backlinks pointing to the absorbed article, and archives it.

## Steps

### 1. Check KB Path

```bash
[ -f ".kb/manifest.json" ] || { echo "Not inside a knowledge base."; exit 1; }
```

**If the output is "Not inside a knowledge base." — stop immediately. Do not proceed to any further steps. Reply only with: "Not inside a knowledge base."**

Otherwise, set `KB_PATH` = `$PWD` for all subsequent steps.

### 2. Determine Mode

**Explicit mode:** If two slugs are provided after `/kb-merge` (e.g. `/kb-merge attention attention-mechanism`):
- Set `PAIRS` = `[("attention-mechanism", "attention")]`
  - The article with more entries in its `## Sources` section is `slug-keep`; the other is `slug-absorb`
  - If tied, keep the first slug provided

**Auto mode:** If no arguments are given:
- Run duplicate detection: read `wiki/index.md`, compare all concept slugs for:
  - **Substring match:** one slug is a substring of another
  - **Word overlap:** two slugs share 2+ words when split by `-`
- For each candidate pair, print:
  ```
  Duplicate candidate: `{slug-a}` and `{slug-b}` ({reason})
  Merge? [y/n/skip]:
  ```
  Wait for input. Collect all confirmed pairs into `PAIRS`.
  If the user types `skip`, move to the next pair without merging.
  If no pairs are confirmed, print `Nothing to merge.` and stop.

If either slug in a pair does not have a corresponding file in `wiki/concepts/`, print:
```
Error: wiki/concepts/{slug}.md not found. Check the slug and try again.
```
And skip that pair.

---

### 3. For Each Pair in PAIRS

Process each `(slug-keep, slug-absorb)` pair sequentially.

#### 3a. Read Both Articles

```bash
cat {KB_PATH}/wiki/concepts/{slug-keep}.md
cat {KB_PATH}/wiki/concepts/{slug-absorb}.md
```

#### 3b. Determine Merged Slug

If not already determined in Step 2, compare `## Sources` section length:
- Count the number of `- [[sources/...]]` lines in each article
- `slug-keep` = the slug with more sources
- `slug-absorb` = the other one
- If tied, keep the first slug

#### 3c. Write Merged Article

Write a clean merged article to `{KB_PATH}/wiki/concepts/{slug-keep}.md`:

```markdown
---
tags: [{union of both articles' tags, deduplicated}]
---

# {Title: use slug-keep's title, or synthesize a better one if the merge warrants it}

{Synthesized body: write a single coherent article that incorporates all substantive content
from both articles. Do not include seams like "In the first article..." or "Additionally...".
Write as if it was always one article. Resolve any contradictions explicitly.
Length: match the combined depth of both articles.}

## Connected Concepts
{Union of both articles' Connected Concepts / See Also sections, deduplicated,
formatted as [[concepts/{slug}]]}

## Sources
{Union of both articles' Sources sections, deduplicated,
formatted as [[sources/{slug}]]}
```

#### 3d. Update All Backlinks

Find every file in `wiki/` that references `slug-absorb`:

```bash
grep -rl "{slug-absorb}" {KB_PATH}/wiki/ --include="*.md"
```

For each file found, replace all occurrences of:
- `[[concepts/{slug-absorb}]]` → `[[concepts/{slug-keep}]]`
- `[[{slug-absorb}]]` → `[[concepts/{slug-keep}]]`

Also check `outputs/` for references:
```bash
grep -rl "{slug-absorb}" {KB_PATH}/outputs/ --include="*.md"
```
Apply the same replacements.

#### 3e. Archive Absorbed Article

```bash
mkdir -p {KB_PATH}/wiki/archive
mv {KB_PATH}/wiki/concepts/{slug-absorb}.md {KB_PATH}/wiki/archive/{slug-absorb}.md
```

Prepend a redirect note to the archived file:

```markdown
> Merged into [[concepts/{slug-keep}]] on {YYYY-MM-DD}

---

```

(Keep the original content below the redirect note for reference.)

#### 3f. Update wiki/index.md

1. Remove the line containing `[[concepts/{slug-absorb}]]`
2. Update the line containing `[[concepts/{slug-keep}]]` — refresh its one-line description to reflect the merged scope if needed
3. Add `## Archive` section if it doesn't exist. Append:
   ```
   - [[archive/{slug-absorb}]] — merged into [[concepts/{slug-keep}]] on {date}
   ```

Write the updated index back to disk.

#### 3g. Commit This Merge

```bash
cd {KB_PATH} && git add -A && git commit -m "kb: merge concepts/{slug-absorb} into concepts/{slug-keep}"
```

One commit per merge pair for clean git history.

#### 3h. Print Merge Summary

```
Merged: {slug-absorb} → {slug-keep}
  Backlinks updated: {N} file(s)
  Archived: wiki/archive/{slug-absorb}.md
```

---

### 4. Final Summary

After all pairs are processed:

```
Merge complete.
  {N} concept(s) merged.
  {N} backlink(s) updated across wiki/ and outputs/.
  {N} article(s) archived to wiki/archive/.
```
