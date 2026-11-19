# Context Port

**Know which conversation messages a smaller handoff leaves behind.**

A local, extractive planner for one ChatGPT export conversation: follow its explicit current branch, keep complete messages within a character budget, pin important turns, inspect every node's disposition, and reproduce the plan against the original export.

A local handoff-auditing tool by **walker512**, not a full-platform migration product. It does not log into platforms, import a chat, send data, call a model, summarize meaning, or guarantee useful continuation. It does not transfer attachments. Its budget counts selected Unicode text characters, **not tokens** and not JSON/report overhead.

## Try the labelled synthetic example

Python 3.11+; no runtime dependencies. Run from this folder:

```sh
python -m contextport audit examples/synthetic.json --conversation synthetic-1
python -m contextport pack examples/synthetic.json --conversation synthetic-1 --budget 50 --pin u1 --out handoff.json
python -m contextport verify examples/synthetic.json handoff.json --conversation synthetic-1
python -m contextport report examples/synthetic.json --conversation synthetic-1 --budget 50 --pin u1 --out review.html
```

Open review.html locally. In this fictional example a small budget drops intermediate messages, an alternative branch contains conflicting instructions, and a selected message references an attachment that is not transferred. Pinning the early instruction retains its text explicitly. This is not a real-user sample or usability study.

Outputs must not already exist. The source remains unchanged. The report includes selected private text: preview it before sharing or uploading to another service. The JSON package is a reviewable data format, **not a native import file for another platform**.

## Create an editable handoff with exact quotes

Use the same fictional conversation to build a brief from a human-written spec,
verify it against the original, and export Markdown you can review and copy:

```sh
python -m contextport brief-build examples/synthetic.json examples/briefing-spec.json --conversation synthetic-1 --out briefing.json
python -m contextport brief-verify examples/synthetic.json briefing.json --conversation synthetic-1
python -m contextport brief-text examples/synthetic.json briefing.json --conversation synthetic-1 --out handoff.md
```

Open `handoff.md` in a local text editor. The example includes a goal, a fact
marked as confirmed in the fictional spec, and a to-do, each with quoted source
text. Verification checks that the quotes and the bundle match the supplied
source and spec. It does not check whether a quote supports a claim or whether
that claim is true.

To write your own cards, start with the [editable handoff guide](docs/EDITABLE_HANDOFF.md).
Review both outputs before sharing: JSON retains selected original messages,
and Markdown still contains excerpts. Nothing is sent or imported automatically.

## Boundaries

- Input: a supplied JSON array containing ChatGPT-style mapping/current_node records, maximum 32 MiB and 10000 nodes per conversation. ZIP, Claude, Gemini and other schemas are not supported.
- Missing current_node, cycles, broken parent/child links and duplicate JSON keys stop processing; no branch is guessed.
- The planner keeps a contiguous suffix of eligible user/assistant text messages plus explicit pins. It never truncates a message or automatically invents a summary. Pins can create context gaps; those omissions remain visible.
- A coverage row describes every mapping node: selected, off-branch, structural, unsupported/empty or budget omission. Non-text parts, unsupported content types, excluded roles and metadata are marked. This does not enumerate every unknown export field or recover content absent from the export.
- Attachments are not copied, fetched, opened or checked for existence. A non-text warning does not prove a file is missing.
- Verification reproduces exactly this deterministic plan against the supplied original. Hashes are not signatures and do not prove authorship, truth, complete source export or semantic adequacy.
- Do not paste a whole account archive into an external model to use this tool. No external service is needed.

## What this adds to an existing workflow

Context Port packages character budgeting, pinned complete messages, a per-node omission ledger and original-input plan reproduction in one local CLI. You can inspect a smaller handoff without writing a custom planning adapter. That is its bounded, practical advantage; these ideas are not claimed to be novel.

Existing tools do more in other directions. [ChatGPT JSON Tree Viewer](https://github.com/akivacp/chatgpt-json-tree-viewer) offers a richer branch browser; [chatgpt-migrator](https://github.com/Redherring9/chatgpt-migrator) performs actual destination transfers; [SMB migration plugin](https://github.com/SMB-Team-Technology/ChatGPT-migration-plugin) already checks graph integrity and refuses to guess an invalid branch.

A private six-case synthetic comparison found that Redherring's parser plus an explicitly custom-written budget/pin/coverage adapter could match the measured handoff outcomes. Context Port is not more capable than that combined workflow; it provides these controls ready to use. No human time saving, semantic quality, adoption or destination import advantage has been measured. This is not evidence that every competing tool lacks these controls. The comparison adapter shared canonical serialization code, so it was not an independent cryptographic verification implementation.

## Install and use your own export

Download and extract the source ZIP, open a terminal in the extracted `context-port` folder, and run `python -m contextport --help`. Use `python3` on systems where that is the Python 3 command, or `py -3` on Windows. Python 3.11+ is required. No pip installation, API key or service is needed. This is a source-directory distribution, not a package published on PyPI.

Extract your official export locally first; pass its JSON array file, not the ZIP. Find the conversation's `id` (or `conversation_id`) in that local file. Run `audit` using that ID to see node IDs, then use `--pin NODE_ID` for each turn you want to retain. `--pin` can be repeated. Quote paths containing spaces. All example commands above use fictional data.

If pins exceed the budget or no complete message fits, planning stops rather than truncating content. Choose a larger budget or fewer pins. If an output already exists, choose a new filename; the tool does not overwrite it. If graph validation fails, check your export/schema rather than guessing a different active branch. Review the HTML and omissions before using the package. There is no automatic destination import or prompt generation.

## Validation and remaining limits

The original planner was tested privately on Python 3.11 and 3.13: Linux and macOS 15 Intel each executed all 29 regression tests; Windows executed 28 and skipped the FIFO test because `os.mkfifo` is unavailable. Skipping that test is not Windows FIFO security verification. Apple Silicon was not tested.

The extracted frozen package passed 16 CLI/static-report browser checks with Chromium sandbox enabled. Reports at 1500px and 390px were independently inspected. These are synthetic fixtures, not real-user conversations, real-phone testing, full accessibility testing or destination import tests. Independent safety review covered strict numeric-versus-boolean verification, finite-number/depth handling, special-file refusal and content-free error messages. The 29 original planner regressions are included under `tests/`; private CI artifacts are not distributed.

These historical results cover the original planner, not a fresh cross-platform run of the editable brief. See the [brief validation scope](docs/EDITABLE_HANDOFF.md#privacy-and-validation) for its synthetic checks.

Outputs intentionally contain selected conversation text, node identifiers and hashes; **identifiers and hashes are not anonymization**. Review all generated material before sharing. A hash is not a signature: someone able to replace both source and package can produce a matching pair. There is no redaction, encryption, secure deletion, authenticity check or truth/semantic verification.

## License

MIT, copyright 2026 walker512. No competitor code or private test data is included in this distribution. See LICENSE.

## Run the included tests

From the extracted source folder, with Python 3.11+:

```sh
python -m unittest discover -s tests -v
```

The suite uses only Python's standard library and temporary synthetic files. It covers active-branch selection, complete-message budgets and pins, per-node coverage, malformed graphs/JSON, changed source/package rejection, numeric/boolean type confusion, non-finite numbers including exponent overflow, bounded nesting, FIFO/symlink refusal, sanitized errors, and the CLI pack/verify/report/no-overwrite loop. The fixture is constructed in tests/test_contextport.py; examples/synthetic.json is the separate runnable demo. Neither contains real conversations or secrets.

FIFO testing skips on platforms without os.mkfifo; symlink testing skips if the OS disallows creating one. Read skip messages: a skipped case is not a pass for that capability. The public suite also covers brief creation, verification and Markdown export using synthetic data.
