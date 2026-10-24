# Resolution evidence — what it checks and what it will not decide

## The problem

A prediction market resolves YES. Someone with money on NO asks "on what grounds?" The answer
is usually a link and a shrug. The actual question is narrower: *did the resolver read sources
that say what they claim, and do those sources agree?*

## What it checks

Input: the market, the rules (with a hash), the declared outcome, and the sources the resolver
used — each with a claim, a quote, a URL and a retrieval time.

| Code | Severity | Meaning |
|---|---|---|
| `sources_conflict` | error | the sources name different outcomes |
| `source_contradicts` | error | every source disagrees with the declared outcome |
| `missing_evidence` | error | a source has no quote: the claim cannot be checked against text |
| `no_sources` | error | nothing was provided to support the outcome |
| `unknown_outcome` | error | the declared outcome is not YES/NO/INVALID/VOID |
| `rules_hash_mismatch` | error | declared rules hash ≠ hash of the file provided |
| `rules_unchecked` / `rules_file_missing` | warning | a hash without the file, or the file is gone |
| `premature_resolution` | warning | declared before the market deadline |
| `pre_deadline_source` | warning | the source was read before the deadline: it cannot settle it |
| `single_source` | warning | fewer than two independent sources |
| `unknown_source_claim` | warning | a source claim that is not a market outcome |

## Verdicts

- `supported` — at least two independent sources agree with the declaration, each with a quote.
- `disputed` — the sources disagree with each other, or all of them disagree with the declaration.
- `single_source` — everything agrees but only one document was read.
- `insufficient` — nothing to weigh: no sources, no quotes, or an unknown outcome.

There is no "probably". A conflict is reported as a conflict; the tool does not average, score or
pick a winner.

## What it never does

- No trading, no position, no market contract interaction.
- No judgement about what *should* have happened — only what the provided documents say.
- No weight by source "reputation": a source is a name, a quote and a hash, nothing more.
- No claim that a missing source does not matter. It says what it read.

## Signature

The report is canonical and Ed25519-signed (`--key`). The disclaimer is inside the signature:
a report with an edited disclaimer does not verify.

## Run

```bash
nidhipati-resolve report examples/resolve.example.json --key keys/private.pem --markdown report.md
```

Exit code: `0` supported, `1` anything else, `2` bad input.
