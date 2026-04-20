---
name: kb-import
description: Import an existing Obsidian vault into the knowledge base. Inspects each note and routes it intelligently — structured concept articles go to wiki/concepts/, raw research notes go to raw/notes/ for later compilation. Usage: /kb-import <vault-path>
trigger: /kb-import
---

# KB Import

Import an existing Obsidian vault into the knowledge base. Each note is inspected and routed based on its content — the LLM decides whether it belongs in the compiled wiki or the raw staging area.

## Steps

### 1. Check KB Path

```bash
[ -f ".kb/manifest.json" ] || { echo "Not inside a knowledge base."; exit 1; }
```

**If the output is "Not inside a knowledge base." — stop immediately. Do not proceed to any further steps. Reply only with: "Not inside a knowledge base."**

Otherwise, set `KB_PATH` = `$PWD` for all subsequent steps.

### 2. Validate Source Vault

The argument after `/kb-import` is the source vault path. Expand `~` if present.

```bash
ls {VAULT_PATH}
```

If the directory does not exist, print:
```
Error: vault path not found: {VAULT_PATH}
```
And stop.

If `.kb/manifest.json` exists inside the vault, print:
```
This looks like a KB vault, not a plain Obsidian vault.
Use /kb-merge-vault {VAULT_PATH} instead.
```
And stop.

### 3. Scan Vault Files

Find all `.md` files in the vault, excluding hidden directories:

```bash
find {VAULT_PATH} -name "*.md" -not -path "*/.obsidian/*" -not -path "*/.trash/*" | sort
```

If no files are found, print `No markdown files found in vault.` and stop.

Set `TOTAL` = count of files found.
Print: `Found {TOTAL} notes to import. Inspecting...`

### 4. Read Manifest

```bash
cat {KB_PATH}/.kb/manifest.json
```

Keep in memory — you will update it as notes are routed to `raw/`.

### 5. Read Existing Index

```bash
cat {KB_PATH}/wiki/index.md
```

Keep in memory — you will append entries for notes routed to `wiki/concepts/`.

### 6. Classify and Route Each Note

For each `.md` file found in Step 3, read it and classify it:

**Classification criteria:**

| Route | Signals |
|---|---|
| `wiki/concepts/` | Has a clear concept definition or explanation; written as a reference article; structured with headings; could stand alone as documentation |
| `raw/notes/` | Personal shorthand or fleeting thoughts; incomplete sentences; meeting notes or journal entries; cites a specific external source (paper, article, book, URL) |

When in doubt between the two, route to `raw/notes/` — it will be compiled later.

---

#### If routed to `wiki/concepts/`:

1. Generate `SLUG` from the filename or first `#` heading: lowercase, replace spaces with `-`, strip special characters.
2. Check if `{KB_PATH}/wiki/concepts/{SLUG}.md` already exists:
   - If yes: skip this file, log as `skipped (concept already exists): {SLUG}`
3. Write to `{KB_PATH}/wiki/concepts/{SLUG}.md`:
   - Preserve all existing content exactly
   - If YAML frontmatter is missing, prepend:
     ```yaml
     ---
     tags: [{infer 2-4 relevant tags from content}]
     imported_from: {original filename}
     ---
     ```
   - If frontmatter exists, add `imported_from: {original filename}` to it
4. Append to `wiki/index.md` under `## Concepts` (only if not already present):
   ```
   - [[concepts/{SLUG}]] — {one-line description inferred from content}
   ```

---

#### If routed to `raw/notes/`:

1. Generate `SLUG` from the filename: lowercase, replace spaces with `-`, strip special characters.
2. If `{KB_PATH}/raw/notes/{SLUG}.md` already exists, append `-imported` to the slug.
3. Write to `{KB_PATH}/raw/notes/{SLUG}.md`:
   - Prepend YAML frontmatter:
     ```yaml
     ---
     source: imported from {original file path}
     ingested_at: {current UTC ISO timestamp}
     type: note
     status: uncompiled
     imported_from: {original filename}
     ---
     ```
   - Append original file content below frontmatter
4. Register in manifest:
   ```json
   "raw/notes/{SLUG}.md": {
     "status": "uncompiled",
     "ingested_at": "{current UTC ISO timestamp}",
     "source": "imported from {original file path}",
     "type": "note"
   }
   ```

---

### 7. Write Updated Files

1. Write the updated `wiki/index.md` back to disk
2. Write the updated `.kb/manifest.json` back to disk

### 8. Commit

```bash
cd {KB_PATH} && git add -A && git commit -m "kb: import {N} notes from {VAULT_PATH}"
```

### 9. Print Summary

```
Import complete from: {VAULT_PATH}
─────────────────────────────────
  → wiki/concepts/   {N} notes (ready to browse in Obsidian)
  → raw/notes/       {N} notes (ready to compile)
     Skipped:        {N} (already existed)

Run /kb-compile to process the raw notes into the wiki.
```

### 10. Prompt for Compile

Ask: `Run /kb-compile now to process the imported raw notes? [y/n]`

If yes, invoke `/kb-compile`.
If no, stop.
