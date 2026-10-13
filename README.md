# Vault Semantic Search

**Find notes by meaning, in Hebrew and English, with a local index that can never see your private folder.**

Search in a notes vault is usually lexical: grep, titles, tags. It doesn't know that a word,
its synonym and its translation are the same idea, so a question asked in Hebrew never finds a
page written in English, and the other way round. This repo adds a small semantic layer: local
embeddings (Ollama + `bge-m3`), a numpy file, and a search command that returns paths for an
agent to read.

Part of [Digital Brain](https://github.com/OferBlum/personal-digital-brain-with-ai).

## Hebrew ⇄ English

Built for a vault written in a mix of Hebrew and English. Ask in either language, and find pages
in both. Real queries against a test vault, top result:

| Query | Found |
|-------|-------|
| `vector database` | `7 - Wikipedia/מסד נתונים וקטורי.md` (Hebrew page) |
| `איך ללמוד מהר` ("how to learn fast") | `2 - Notes/Learning.md` (English page) |
| `how do I study effectively` | `2 - Notes/Learning.md` (the page never says "study") |

`bge-m3` is a multilingual embedding model, so this isn't limited to Hebrew. Hebrew is what it was
built and tested on. Filenames are Unicode-normalized (NFC), so the same Hebrew title always maps
to the same path.

## The idea

- **An allowlist, not a filter.** The indexer lists only the top level of three content
  folders. It never walks the vault and filters afterwards, so the private folder's filenames
  are never even listed, and the boundary module doesn't need to know that folder's name.
  Symlinks are refused, and every read opens each path component with `O_NOFOLLOW`.
- **A locator, not a source of truth.** Search returns paths only: no excerpts, no scores.
  The agent opens the files and reads them, so an answer is always grounded in the real
  page, never in a stale cached chunk.
- **Disposable and atomic.** The index is derived data. Each build writes a new generation
  folder, then swaps one pointer file (`active.json`). A failed build leaves the previous
  index serving. Delete `vector-out/` and rebuild at any time.
- **No vector database.** At a few thousand chunks, numpy cosine over everything takes under
  10 ms. faiss or chroma would add a dependency for no gain.

## How it works

```text
1 - Topics/  2 - Notes/  7 - Wikipedia/      (top-level *.md only)
        │
        ▼  safe_input.py: allowlist, no symlinks, O_NOFOLLOW reads, frontmatter
embed_index.py ── chunk by heading, prefix "title · background" ──► Ollama bge-m3
        │                                                           (local)
        ▼
vector-out/<generation>/ vectors.npy · chunks.jsonl · meta.json
vector-out/active.json   ◄── swapped atomically after a full build
        │
        ▼
vsearch.py "question"  ──►  2 - Notes/Learning.md
                            7 - Wikipedia/Vector database.md
```

Every chunk is prefixed with its page's title and `background` field. That's the cheapest
cross-language bridge: a Hebrew title travels with an English body, and the other way round.

Before reading any cached text, search re-checks the generation's schema and every stored path
against the boundary. If a source has since left the boundary, the whole index is treated as
unavailable rather than filtered.

## Files

```text
0 - System/scripts/
  safe_input.py                   # the boundary: folder allowlist, no-follow reader, header parser
  embed_index.py                  # incremental build; --rebuild --status --audit --check --changes
  vsearch.py                      # search; --k, --folder, --json (paths only)
  reindex.sh                      # prints change counts, checks Ollama, then updates the index
  vault-python.sh                 # runs the scripts in their own venv; --setup creates it
  vault-search-requirements.txt   # numpy, PyYAML
  test_safe_index.py              # boundary tests against a throwaway vault, with a stub Ollama
.claude/
  commands/reindex.md             # /reindex
  skills/vault-search/SKILL.md    # when and how an agent should search
```

The allowed folders are a constant at the top of `safe_input.py`. Set `OLLAMA_HOST` if Ollama
isn't on `localhost:11434`, and `VAULT_EMBED_MODEL` to use another embedding model.

## Quickstart

1. Copy `0 - System/` and `.claude/` into your vault, then `ollama pull bge-m3`.
2. `bash "0 - System/scripts/vault-python.sh" --setup`, then build the index:
   `bash "0 - System/scripts/reindex.sh"`.
3. Search: `bash "0 - System/scripts/vault-python.sh" "0 - System/scripts/vsearch.py" "your question"`.
   After editing notes, run `/reindex` in Claude Code.

Tests: `python3 -m unittest discover -s "0 - System/scripts" -p "test_*.py"` (needs numpy and PyYAML).

## License

MIT, see [LICENSE](LICENSE).
