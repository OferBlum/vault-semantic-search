---
name: vault-search
description: Find vault files by meaning with the local semantic index — crosses languages and synonyms. Use for "where did I write about…", "what do I have on…", or finding related-link candidates.
compatibility: Needs Ollama running locally with the bge-m3 model, and the index built by embed_index.py. Run from the vault root.
---

# Vault Search

## When to use
Find vault content by meaning: "where did I write about…", "what do I have on…", or
related-link candidates for a page. The index is a locator, not a source of truth.

## Boundaries
- **Allowlist only:** the index covers top-level Markdown in `7 - Wikipedia`, `2 - Notes` and
  `1 - Topics`. Nothing else is indexed, so nothing else can be found here. Don't go looking
  for it another way.
- **No scanning:** never scan the vault root or follow symlinks.
- **Read-only:** finding a file never authorizes editing it.

## Usage
```text
bash "0 - System/scripts/vault-python.sh" "0 - System/scripts/vsearch.py" "question" --json --k 8
```
`--json` returns a JSON array of paths only: no excerpts, no scores. Add `--folder "<folder>"`
only when the user asks to restrict the search.

## Procedure
1. **Search** the main idea and, when useful, a distinct secondary idea in other words.
2. **Read** the relevant candidates before answering or linking. Similarity is not identity:
   two pages about the same idea are not duplicates until their titles, authors or sources match.
3. **Fall back.** If the index or Ollama is unavailable, say so and fall back to a targeted
   filename or text search inside the allowed folders. Never build a second index or rebuild
   on your own. Weak or empty results don't prove that nothing exists, so try another phrasing.
4. **Cite** real files by their vault-relative paths, and distinguish the owner's own notes from
   compiled summaries.

## Index maintenance
Refresh only when asked, or as an approved step of a content update: `/reindex`, or
`bash "0 - System/scripts/reindex.sh"`. Embeddings stay local. Report what changed and the chunk count.
