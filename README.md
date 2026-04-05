# LLM Knowledge Base

A self-managed personal knowledge base powered by Claude Code. You feed it raw content — URLs, PDFs, images, notes — and the LLM handles all organization: tagging, summarizing, linking concepts, and answering questions. You never edit the wiki directly.

Uses **Obsidian** as the viewer/frontend.

---

## Setup

```bash
bash setup.sh ~/knowledge-base
```

This will:
- Create the KB directory structure at `~/knowledge-base` (or any path you pass)
- Initialize it as a git repo
- Write `~/.claude/kb-config.json` pointing to that directory
- Install the three skills into `~/.claude/skills/`

Then open `~/knowledge-base` as a vault in Obsidian.

---

## Skills

### `/kb-ingest <source>`

Stage content into `raw/`. Does not compile yet.

```
/kb-ingest https://arxiv.org/abs/1706.03762
/kb-ingest /path/to/paper.pdf
/kb-ingest /path/to/diagram.png
/kb-ingest Self-attention allows each token to attend to all other tokens regardless of distance
```

Supported input types:
| Input | Where it goes |
|---|---|
| URL (`http://` or `https://`) | `raw/web/` |
| `.pdf` file path | `raw/pdfs/` |
| Image file path (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`) | `raw/images/` |
| Anything else | `raw/notes/` |

Each ingested file gets YAML frontmatter with `source`, `ingested_at`, `type`, and `status: uncompiled`. The file is registered in `.kb/manifest.json`.

---

### `/kb-compile`

Process all uncompiled `raw/` content into the wiki. Run this after ingesting new content.

```
/kb-compile
```

For each uncompiled file, the LLM:
1. Writes a source summary to `wiki/sources/<slug>.md` (summary, tags, key concepts, notable details)
2. Creates or updates concept articles in `wiki/concepts/<concept>.md` with Obsidian `[[backlinks]]`
3. Appends entries to `wiki/index.md`
4. Updates `.kb/manifest.json` → `status: compiled`
5. Commits the changes to git

Incremental — only processes new content. Safe to re-run; prints `Nothing to compile.` if everything is up to date.

---

### `/kb-ask <question>`

Ask a question against the wiki.

```
/kb-ask what is the attention mechanism?
/kb-ask how does RLHF relate to transformers?
/kb-ask summarize what we know about scaling laws
```

The LLM:
1. Reads `wiki/index.md` (the navigation layer — never loads the full wiki)
2. Selects 3–5 most relevant articles
3. Synthesizes a grounded answer with `[[wiki-link]]` citations
4. Saves the answer to `outputs/YYYY-MM-DD-<slug>.md`
5. Indexes the output in `wiki/index.md` so future queries can build on it
6. Commits to git

---

## Directory Structure

```
~/knowledge-base/
├── raw/                    # staged source content (managed by /kb-ingest)
│   ├── web/               # web articles as .md
│   ├── pdfs/              # PDFs + extracted text
│   ├── images/            # images + description sidecars
│   └── notes/             # freeform text notes
├── wiki/                   # compiled knowledge (managed by /kb-compile)
│   ├── index.md           # master index — one-line summary per article
│   ├── concepts/          # one .md per concept, with [[backlinks]]
│   └── sources/           # one .md per raw source
├── outputs/                # Q&A answers (managed by /kb-ask)
└── .kb/
    └── manifest.json      # compilation state tracker
```

> The LLM owns `wiki/` and `outputs/`. You own `raw/`. Don't edit the wiki manually.

---

## Typical Workflow

```
# 1. Ingest some content
/kb-ingest https://lilianweng.github.io/posts/2023-06-23-agent/
/kb-ingest https://arxiv.org/abs/2005.14165
/kb-ingest My intuition: chain-of-thought works because it externalizes intermediate reasoning steps

# 2. Compile into the wiki
/kb-compile

# 3. Ask questions
/kb-ask what are the key components of an LLM agent?
/kb-ask how does chain-of-thought prompting work?
```

Repeat. The wiki grows smarter with every ingest + compile cycle. Q&A answers are indexed back in, so future queries compound on past ones.

---

## Obsidian Tips

- Use the **Graph View** to see how concepts link to each other via `[[backlinks]]`
- Use the **Backlinks panel** on any concept article to see all sources that mention it
- The `wiki/index.md` file is a good home/dashboard note — pin it
- Install the **Marp** plugin if you later want to render outputs as slideshows
