#!/usr/bin/env bash
set -e

KB_PATH="${1:-$HOME/knowledge-base}"
KB_PATH="${KB_PATH/#\~/$HOME}"

echo "Initializing knowledge base at: $KB_PATH"

# Create directory structure
mkdir -p "$KB_PATH/raw/web"
mkdir -p "$KB_PATH/raw/pdfs"
mkdir -p "$KB_PATH/raw/images"
mkdir -p "$KB_PATH/raw/notes"
mkdir -p "$KB_PATH/wiki/concepts"
mkdir -p "$KB_PATH/wiki/sources"
mkdir -p "$KB_PATH/outputs"
mkdir -p "$KB_PATH/.kb"

# Initialize git repo if not already one
if [ ! -d "$KB_PATH/.git" ]; then
  git -C "$KB_PATH" init
  echo "Initialized git repository."
fi

# Create manifest if it doesn't exist
MANIFEST="$KB_PATH/.kb/manifest.json"
if [ ! -f "$MANIFEST" ]; then
  echo '{}' > "$MANIFEST"
  echo "Created manifest.json"
fi

# Create wiki index if it doesn't exist
INDEX="$KB_PATH/wiki/index.md"
if [ ! -f "$INDEX" ]; then
  cat > "$INDEX" << 'EOF'
# Knowledge Base Index

## Concepts

## Sources

## Outputs
EOF
  echo "Created wiki/index.md"
fi

# Create .gitignore
GITIGNORE="$KB_PATH/.gitignore"
if [ ! -f "$GITIGNORE" ]; then
  cat > "$GITIGNORE" << 'EOF'
.DS_Store
*.swp
EOF
fi

# Write config
CONFIG="$HOME/.claude/kb-config.json"
mkdir -p "$HOME/.claude"
cat > "$CONFIG" << EOF
{
  "kb_path": "$KB_PATH"
}
EOF
echo "Wrote config to $CONFIG"

# Install skills
SKILLS_DIR="$HOME/.claude/skills"
mkdir -p "$SKILLS_DIR"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/kb-ingest.md" "$SKILLS_DIR/kb-ingest.md"
cp "$SCRIPT_DIR/kb-compile.md" "$SKILLS_DIR/kb-compile.md"
cp "$SCRIPT_DIR/kb-ask.md" "$SKILLS_DIR/kb-ask.md"
echo "Installed skills to $SKILLS_DIR"

echo ""
echo "Done! Open $KB_PATH in Obsidian."
echo "Skills available: /kb-ingest, /kb-compile, /kb-ask"
