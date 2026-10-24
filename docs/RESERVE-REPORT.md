# Reserve and NAV report — what it computes, what it refuses

## The problem

An issuer says "fully backed" and links a PDF. A holder cannot multiply a PDF by anything.
The question a holder actually has is arithmetic: *what is the value of the reserve, what is the
supply, and what happens to the ratio when one line is not priced?*

## What it computes

```
value(line) = quantity × price × (1 − haircut)
NAV         = Σ value(reserve lines) − Σ value(liabilitity lines)
ratio       = NAV / supply
verdict     = backed (ratio ≥ 1) · underbacked (ratio < 1) · incomplete (a line has no price)
```

Every input is a string in a JSON file, so the same numbers reproduce the same report byte for
byte (the report is canonical before signing).

## What it refuses

- **A ratio over an unpriced line.** If one reserve line has no price, the verdict is
  `incomplete` and `backing_ratio` is `null`. Excluding the line silently would produce a
  lower NAV and look like a finding; including it would invent a price. Neither is honest.
- **A source that does not exist.** Every line needs a `source`. The report carries
  `sha256:` evidence over the line's own fields, so a line cannot be edited after the fact
  without the hash changing.
- **A statement that does not match.** If a custodian statement hash is given together with the
  file, the file is hashed and compared. A mismatch is an error, not a footnote.
- **A date it does not have.** `as_of` is required. A NAV without a date is not a NAV.

## Findings

| Code | Severity | Meaning |
|---|---|---|
| `unpriced` | error | no price: the ratio is refused |
| `missing_source` | error | the quantity has no stated origin |
| `haircut_out_of_range` | error | haircut outside [0, 1) |
| `missing_supply` | error | no supply: backing cannot be judged |
| `empty_reserve` | error | the reserve has no lines |
| `underbacked` | error | the reserve covers less than the supply |
| `statement_hash_mismatch` | error | declared hash ≠ hash of the file |
| `stale_price` | warning | price older than 3 days before `as_of` |
| `duplicate_asset` | warning | the same asset appears twice — check it is not counted twice |
| `statement_unchecked` | warning | a hash was given without the file |

## Honest limits of v0.3

- No chain read: token supply comes from the issuer's input. `onchain_verified` is absent
  because nothing was verified on-chain.
- No custodian confirmation: the statement is checked for hash equality with the file you
  provide, not with the custodian.
- No legal opinion, no statutory audit. This is arithmetic with evidence, and the disclaimer
  travels inside the signed document so it cannot be stripped quietly.

## Partner and legal checklist (before signing a paid report)

What we require from an issuer, and what we will not do:

1. **Named legal entity and jurisdiction** on the report. "The team" is not an issuer.
2. **Custodian confirmation channel** — a contact at the custodian who can confirm the account
   exists. Without it the report says `statement_unchecked`.
3. **Written permission** to name the custodian. Otherwise the custodian is described by role,
   not by name.
4. **A stated NAV methodology** from the issuer; ours is published and must match, or the
   difference must be listed as a finding.
5. **A cut-off date and time zone.** "As of yesterday" is not a date.
6. **No forward-looking statements** in the report: no "expected to remain backed".
7. **No marketing use of the report** beyond the version we signed. A report with an edited
   disclaimer is not our report.
8. **Refusal cases:** we do not issue a report when the issuer refuses to name the entity, when
   a material line has no independent source, or when the request is to "make the ratio work".
   Those are recorded as declined, with the reason.

## Run

```bash
nidhipati-reserve report examples/reserve.example.json \\
  --key keys/private.pem --out report.json --markdown report.md
```

Exit code: `0` backed with no error, `1` findings, `2` bad input.
