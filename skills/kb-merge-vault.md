---
name: kb-merge-vault
description: Merge a second KB vault into the current one. Copies non-conflicting content, auto-merges conflicting concept articles using LLM synthesis, merges manifests and index, and resets reflect state for a full re-synthesis. Usage: /kb-merge-vault <vault-path>
trigger: /kb-merge-vault
---

# KB Merge Vault

Merge a second KB vault into the current one. Handles conflicts by auto-merging concept and source articles using LLM synthesis. Resets reflect state so the next `/kb-reflect` discovers connections across the merged content.

## Steps

### 1. Derive KB Path

Invoke `/kb-path` to get `KB_PATH` (primary vault).

### 2. Validate Source Vault

The argument after `/kb-merge-vault` is the secondary vault path. Expand `~` if present.
Set this as `SOURCE_PATH`.

```bash
ls {SOURCE_PATH}/.kb/manifest.json
```

If the file does not exist, print:
```
Error: {SOURCE_PATH} does not look like a KB vault (no .kb/manifest.json found).
If this is a plain Obsidian vault, use /kb-import {SOURCE_PATH} instead.
```
And stop.

If `SOURCE_PATH` resolves to the same directory as `KB_PATH`, print:
```
Error: source and destination are the same vault.
```
And stop.

### 3. Load Both Manifests and Indexes

```bash
cat {KB_PATH}/.kb/manifest.json
cat {SOURCE_PATH}/.kb/manifest.json
cat {KB_PATH}/wiki/index.md
cat {SOURCE_PATH}/wiki/index.md
```

Keep all four in memory.

Initialize counters:
```
copied: 0
merged: 0
skipped: 0
```

---

### 4. Merge raw/

For each file in `{SOURCE_PATH}/raw/` (all subdirectories):

1. Compute the relative path (e.g. `raw/web/some-article.md`)
2. If `{KB_PATH}/{relative_path}` does **not** exist:
   - Copy the file: `cp "{SOURCE_PATH}/{relative_path}" "{KB_PATH}/{relative_path}"`
   - Increment `copied`
3. If it **does** exist:
   - Log as skipped: `raw/{relative_path} (duplicate filename)`
   - Increment `skipped`

---

### 5. Merge wiki/sources/

For each `.md` file in `{SOURCE_PATH}/wiki/sources/`:

1. Set `SLUG` = filename without extension
2. If `{KB_PATH}/wiki/sources/{SLUG}.md` does **not** exist:
   - Copy the file
   - Increment `copied`
3. If it **does** exist:
   - Read both files
   - Write a merged source summary to `{KB_PATH}/wiki/sources/{SLUG}.md`:
     - **Summary**: synthesize both summaries into one
     - **Tags**: union of both tag lists, deduplicated
     - **Key Concepts**: union of both concept lists, deduplicated
     - **Notable Details**: combine both, removing exact duplicates
     - **Backlinks**: union of both source file references
   - Increment `merged`

---

### 6. Merge wiki/concepts/

For each `.md` file in `{SOURCE_PATH}/wiki/concepts/`:

1. Set `SLUG` = filename without extension
2. If `{KB_PATH}/wiki/concepts/{SLUG}.md` does **not** exist:
   - Copy the file
   - Increment `copied`
3. If it **does** exist:
   - Read both concept articles
   - Write a clean merged article to `{KB_PATH}/wiki/concepts/{SLUG}.md`:
     - **Tags**: union of both tag lists, deduplicated
     - **Body**: synthesize both bodies into one coherent article — no seams, no duplication, resolve any contradictions explicitly
     - **Connected Concepts**: union of both lists, deduplicated
     - **Sources**: union of both `## Sources` sections, deduplicated
   - Increment `merged`

---

### 7. Copy outputs/

For each file in `{SOURCE_PATH}/outputs/`:

```bash
cp "{SOURCE_PATH}/outputs/{filename}" "{KB_PATH}/outputs/{filename}"
```

Filenames are timestamp-prefixed (`YYYY-MM-DD-*`) so conflicts are extremely unlikely. If a filename already exists in `{KB_PATH}/outputs/`, append `-merged` before the extension.
Increment `copied` for each file.

---

### 8. Copy wiki/archive/

For each `.md` file in `{SOURCE_PATH}/wiki/archive/` (if the directory exists):

- If `{KB_PATH}/wiki/archive/{filename}` does not exist: copy it
- If it exists: skip (archived articles are historical, no merge needed)

---

### 9. Merge manifest.json

Merge the two manifests:

For each key in the source manifest:
- If the key does **not** exist in the primary manifest: add the entry as-is
- If the key **does** exist in both:
  - Keep the entry with `status: compiled` if one is compiled and one is not
  - If both are compiled: keep the one with the more recent `compiled_at` timestamp
  - If both are uncompiled: keep the primary vault's entry

Write the merged manifest back to `{KB_PATH}/.kb/manifest.json`.

---

### 10. Merge wiki/index.md

Merge the two index files section by section.

For each section (`## Concepts`, `## Sources`, `## Outputs`, `## Archive`):
1. Collect all entries from both indexes
2. Deduplicate by the `[[link]]` target (keep the first occurrence if duplicate)
3. Sort alphabetically within each section

Write the merged index back to `{KB_PATH}/wiki/index.md`.

---

### 11. Reset Reflect State

Write to `{KB_PATH}/.kb/reflect_state.json`:

```json
{
  "last_reflected_at": null,
  "synthesized_articles": []
}
```

This ensures the next `/kb-reflect` does a full scan across all merged content, discovering connections between the two vaults.

---

### 12. Commit

```bash
cd {KB_PATH} && git add -A && git commit -m "kb: merge vault from {SOURCE_PATH}"
```

### 13. Print Summary

```
Vault merge complete.
──────────────────────────────────
  Source: {SOURCE_PATH}
  Copied:  {copied} files
  Merged:  {merged} concept/source conflicts resolved
  Skipped: {skipped} raw duplicates

reflect_state reset — run /kb-reflect to synthesize connections across merged content.
```

### 14. Prompt for Reflect

Ask: `Run /kb-reflect now to find connections across the merged vaults? [y/n]`

If yes, invoke `/kb-reflect`.
If no, stop.
