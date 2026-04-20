---
name: kb-path
description: Internal helper. Derives the KB root path by walking up from the current directory until kb-manifest.json is found. Sets KB_PATH for use by other kb-* skills.
trigger: /kb-path
---

# KB Path

Walk up from the current directory to find the nearest ancestor containing `kb-manifest.json`:

```bash
KB_PATH="$PWD"
while [ "$KB_PATH" != "/" ] && [ ! -f "$KB_PATH/kb-manifest.json" ]; do
  KB_PATH="$(dirname "$KB_PATH")"
done
```

If `KB_PATH` is `/`, stop with error: `Not inside a knowledge base.`

Set `KB_PATH` for use by the calling skill.
