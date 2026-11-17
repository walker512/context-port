# Editable, source-linked handoff

Context Port can now assemble **human-authored goals, human-confirmed facts and to-dos** next to exact original quotations. This is local organization, not automatic summarization or fact checking. You decide what the cards mean. Citations locate text; they do not establish that it supports the card or is still true.

## Try it with fictional data

```sh
python -m contextport brief-build examples/synthetic.json examples/briefing-spec.json --conversation synthetic-1 --out briefing.json
python -m contextport brief-verify examples/synthetic.json briefing.json --conversation synthetic-1
python -m contextport brief-text examples/synthetic.json briefing.json --conversation synthetic-1 --out handoff.md
```

The example organizes a local-processing requirement, a CSV-parser goal and an implementation to-do. Its human confirmations are **synthetic fixture values, not evidence of a real user's decisions**. `handoff.md` is plain, source-linked Markdown you can review and copy into a new conversation. No destination is contacted, no attachment is transferred, and no native import format is produced. The JSON contains selected original messages and a complete mapping-node disposition ledger; Markdown carries the cards, their quoted references and that ledger, not every selected original message in full.

## Edit your own handoff

Use only exports you are authorized to process, extracted locally:

```sh
python -m contextport brief-template your-export.json --conversation YOUR_ID --out draft.json
```

The template captures the conversation's current source digest and contains an **empty** `cards` list. Empty drafts cannot be built as finished handoffs. Add 1–100 cards with your local text editor:

```json
{
  "id": "local-processing",
  "kind": "fact",
  "text": "The user requires local processing.",
  "human_confirmed": true,
  "references": [{"node_id": "u1", "start": 12, "end": 28}]
}
```

Each card has exactly these fields. `kind` is `goal`, `fact` or `todo`. Fact cards require explicit boolean `true`; goals/to-dos use `false`. This distinguishes a human's confirmation from the tool's checks, not a verified fact from an unverified fact. To record an uncertain assertion, do not mark it confirmed merely to pass validation; keep it out of fact cards, or create a to-do to check it with an honest supporting reference.

- IDs are unique, 1–80 characters; text is nonblank, at most 4000 characters.
- Each card needs 1–5 different references. References use Python/Unicode **code-point** offsets in the selected message text, zero-based, exclusive end, maximum 4000 characters each. These are not UTF-8 byte offsets, UTF-16 browser indices or grapheme indices. Multi-part text is joined with a newline exactly as in `pack`.
- Inspect message IDs via `audit`, and use the existing `pack` output to inspect exact text. Choose the range explicitly. A reference never searches an alternative branch or guesses a quotation.
- All references must belong to selected eligible user/assistant messages on the explicit current branch. If a needed active-branch message was omitted by the budget, increase `--budget` or add `--pin NODE_ID`. Off-branch or unsupported messages cannot be cited even with a pin.
- Build with `brief-build`, supplying optional `--budget` and repeated `--pin`, like the existing planner. Edit the **specification**, then build into a new output. Do not edit generated cards or citations while retaining an old verification claim.
- Any conversation change, including title or off-branch content, changes its digest and rejects the old specification. Generate a fresh template, recheck your decisions and references, then transfer only what remains appropriate. The tool does not automatically transplant confirmations.
- A matching rebuilt pair is not authenticated. A person who edits the specification and rebuilds can change claims while verification still succeeds. No signatures, identity verification, semantic entailment, truth or review-history service is supplied.

## What verification and budgets mean

`brief-verify` re-runs the original branch/budget/pin planner, checks the full omission ledger and source digest, reconstructs each exact quoted substring and compares the entire typed bundle against the human specification. Numeric `1` cannot replace boolean `true`. It does **not** confirm that the prose is a faithful summary, that an assistant suggestion was adopted, or that anything is still the user's intention. Every card says `semantic_support_verified=false`.

The existing budget counts selected original Unicode text characters only, **not** new human text, duplicated citations, metadata, serialized bytes or tokens. New JSON/Markdown outputs have a separate 4 MiB ceiling; the Markdown export can be refused when markup escaping would exceed that ceiling even if its JSON is valid. The error occurs before creating the requested output file. Reduce the cards/text, then rebuild. Source inputs retain the existing 32 MiB and graph limits.

Markdown encodes markup/control characters in user-provided text to escape explicit Markdown links/images, raw HTML and heading syntax. Renderers may still automatically link plain URLs or email addresses. Inspect any links before opening them; this is not a link sanitizer or a browser-validated UI. Different Markdown renderers may display encoded characters differently; exact raw quotations remain in JSON.

## Privacy and validation

Outputs contain private conversation content, human interpretations, node IDs and hashes. These are not anonymized. Inspect and delete sensitive material before voluntarily sharing; deleting a card does not remove the selected original message from JSON. Reduce the selection if appropriate and inspect the complete package. There is no upload, encryption, redaction, secure deletion, model call or destination login.

The existing 29 public regressions remain unchanged. New synthetic tests cover exact and Unicode references, branch/budget omissions, strict confirmations, stale sources, modified generated quotes, edited human statements, bounded expansion, exclusive UTF-8/LF writes and real CLI template/build/verify/text commands. No new browser, cross-platform, real-conversation usability, destination-import or comparative advantage study is implied.
