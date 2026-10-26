# OUSG as-of-block attestation — scope

**Prepared for:** Ondo Finance (not a client; this is a proposal).
**Asset:** OUSG. **Date:** one date/block chosen by Ondo.
**Status:** draft v0.1, 26.10.2026.

## The gap

The public OUSG Trust & Transparency page says the fund reports may lag up to
three days behind the price update onchain.

A buyer who needs to verify backing at the block where they bought cannot use a
three-day-old report. The report is also a document to read, not a file the buyer
can verify offline.

## What we deliver

1. **Signed JSON attestation** for one asset and one as-of timestamp:
   reserve lines, liabilities/supply, NAV, backing ratio, verdict, source hash per
   line, and the public key.
2. **Human-readable report** with the arithmetic shown: what backs the token,
   haircuts, what could not be priced, and what was not disclosed.
3. **Offline verification**: one command, no server, no account. If the signature
   does not match, the check fails. If one line has no price, the verdict is
   `incomplete` and the ratio is null — never guessed.
4. **Verification note** the buyer or auditor can keep with the file.

## What we need from Ondo

- The NAV Consulting daily report for the chosen date, or a read-only export.
- Reserve/holdings lines and the price source for each line.
- Token supply or fund liabilities at the same timestamp.
- One named owner who signs off on the source data.
- NDA if the data is private. No private keys, no custody, no wallet access.

## Timeline and price

- **10 working days** from complete data.
- **$1,250** for the first three single-asset reports; then $5,000 per asset/date.
- 50% on written scope, 50% on delivery. USDC on Base or Solana; invoice is a
  signed JSON document.
- **Verification guarantee:** if the signed report does not verify offline with
  the published key, the fee is refunded. That is about the file, not about
  Ondo's solvency or the accuracy of its source data.

## What this is not

Not a statutory audit, not legal advice, not an investment opinion, not a
solvency guarantee. Ondo remains responsible for the truth of the source data.
The report says what was checked and what was not; it does not say “100% safe”.

## Contact

Maxim · `maxim.pkk@gmail.com` · written only, no calls required.
Sample (synthetic): https://mrpkk.github.io/nidhipati/sample-reserve-report.html
Generic scope: https://mrpkk.github.io/nidhipati/rwa-scope.pdf
