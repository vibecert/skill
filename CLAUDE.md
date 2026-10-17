# VibeCert

Scores how generative tooling was used to produce one Git branch, against the rubric in `references/rubrics.md`, and publishes the result as a certificate.

## Read this, not that

The evidence bundle runs to tens of thousands of tokens.
Never print it, never read it whole, and never pass it to a subagent.
Use `vibecert-evidence <bundle> <metric>` to get the slice one metric needs, or `python3 -c` to pull single fields.

`references/rubrics.md` is 378 lines.
Read one section with `sed -n '/^### 4\./,/^### 5\./p'` rather than opening the file.

The code is small and each module does one thing, so prefer opening a named module to searching.
The map below is there to make that choice without looking.

## Pipeline

Five entry points run on the author's machine, each consuming the previous one's output, two run on the site, and one runs in a consumer's CI.
Run them with `uv run --project <this>/scripts`.

| Command | In | Out |
| --- | --- | --- |
| `vibecert` | a repository and base | the evidence bundle, `vibecert/evidence@2` |
| `vibecert-metrics` | the bundle | bands for the three countable metrics |
| `vibecert-evidence` | the bundle, a metric name | just what that metric is scored from |
| `vibecert-score` | the bundle, judged bands | the certificate, as markdown or `vibecert/certificate@2` |
| `vibecert-publish` | the certificate, a directory | `<id>/score.json`, ready to submit |
| `vibecert-accept` | a submitted checkout, its changed paths and submitter | the identifier, or every problem |
| `vibecert-build` | the site checkout, a directory | every page, score and badge, and the root page |
| `vibecert-verify` | a pull request's checkout, its branch and base | the identifier, or every reason its certificate does not pass |

`vibecert-publish` writes a file and nothing else.
Submitting it is the skill's job, as a pull request to the site, and `SKILL.md` holds that sequence.
The site's workflows run `vibecert-accept` on each pull request and `vibecert-build` on every push to `main`.
`vibecert-verify` passes only a certified score at or above the threshold whose `head` is the checked-out commit.

## Module map

Collection, which turns a repository and its transcripts into facts:

- `git_repository.py` reads the branch, read-only. `transcript.py` parses Claude Code sessions. `attribution.py` splits the diff into generated and human lines. `revisions.py` counts rewrites that followed a human message. `comments.py`, `criticality.py`, `risk.py`, `guidelines.py` each derive one weight or metric input. `collector.py` assembles them into the bundle.

Scoring, which turns facts into bands and a number:

- `metrics.py` bands metrics 3, 5 and 6. `weights.py` holds the gate and the three weights. `certificate.py` applies the lookup table and produces the document. `evidence.py` projects the bundle for the three judged metrics.

Output:

- `render.py` for the terminal and the pasteable snippets, `page.py` and `assets/certificate.css` for the published page, `publish.py` for the submitted score and the site build, `site.py` for addresses.

Site acceptance:

- `submission.py` checks a pull request to the site. `ownership.py` finds who first published an identifier.

Shared:

- `rubric.py` holds every threshold. `detection.py` holds detection vocabulary: comment markers, check classes, risk severity, import patterns. `bundle_types.py` and `certificate_types.py` are the two pydantic contracts. `vibecert_types.py` holds internal dataclasses. `json_values.py` narrows decoded JSON without `Any`.

## Where the numbers live

Every threshold is in `rubric.py` as `Thresholds`, and every one is also stated in `references/rubrics.md` with its source.
`tests/test_rubric_agreement.py` fails if the two disagree, so change both together.

The lookup table that turns a raw band into an adjusted one is `Thresholds.LOOKUP`, and its reasoning is under "The lookup table" in the rubric.

## Who scores what

Three metrics are deterministic and live in `metrics.py`: output amendments, secondary tool usage, generative comments.
Three need judgement and are scored by one subagent each, dispatched by `SKILL.md`: follow-up questions, coding guidelines, prompt granularity.
Each subagent sees only its own anchors and its own evidence slice, so one metric cannot colour another.

All weights, the gate and the arithmetic are deterministic.

## Conventions

The house rules in `~/.claude/rules` apply, and the Python ones are strict: object orientation throughout, full type hints, no `Any`, no `@property`, getters rather than attribute access, Google docstrings on public methods only, and none on protected ones.
`scripts/pyproject.toml` enforces `E,F,I,D,ANN` at 88 columns.

Docstrings are a summary line plus `Args`, `Returns` and `Raises`, where they apply.
Explanatory paragraphs belong in the rubric, not beside the code.

## Decisions already settled

Do not re-open these without being asked.
Each cost discussion to reach, and the reason matters more than the choice.

The score is a plain mean of the adjusted bands, with no tier, letter or cap.
A capping rule was considered and rejected: the author preferred one honest number against a published rubric over a word that hides it.

Thresholds are absolute and derived from published measurement, not calibrated against the author's own history.
Calibrating against one person's past makes band 2 mean "typical for me", which cannot be compared with anything.
Sources are listed under "Basis of thresholds" in the rubric.

Criticality is a percentile within the repository, not a count of importers.
Five importers makes a file central in a twenty-file package and peripheral in a thousand-file one, so an absolute count does not travel.

The three weights combine by maximum, because one demanding dimension is enough to raise the stakes.

Metric 3 counts revisions that followed a human message, not lines left over after subtracting tool edits.
Subtraction reported a third of a wholly generated branch as hand-written, because a formatter rewrites generated lines after they are generated.

Metric 4's median excludes prompts that produced no output.
Including them drove it to zero on any branch that was interrogated, which would have scored every branch 3.

Metric 5 is scored against the classes of check the diff's file types admit, not against an absolute.
Markdown has no unit tests, and a branch should not be marked down for the language it is written in.

Risk findings come from ruff's bandit ruleset rather than patterns written here, so the catalogue is maintained upstream.
Hand-rolled patterns flagged `.gitignore` and `uv.lock` as network risks.
`S101` is suppressed because an assertion is a finding in shipped code and an idiom in a test suite.

`rubric.py` holds thresholds; `detection.py` holds domain facts such as comment markers and check commands.
A metric should band emitted facts, not do its own detection.

Certificates are served from `https://vibecert.github.io` by default, which the skill passes as `--site-url` on every `vibecert-score` call.
`SiteAddress.derive` still computes the author's own `<owner>.github.io/vibecert`, but the skill overrides it unless the author names somewhere else.
The site root deliberately does not list certificates: listing them would make private ones enumerable and undo the redaction.

The tool generates files; the skill transports them.
Everything else here is read-only by construction, and the certifier must not be able to modify what it scores.

Only a certificate whose `certified` is true is published: `vibecert-publish` refuses one that is not, and so does the site.
An uncertified one has a `null` score, and the author is told the gate's reason instead.

The shared site vouches for a submission's form, its certification and who submitted it, never for its evidence.
A score is self-assessed, and the site cannot recompute it without the author's transcripts.

The owner of an identifier is the author of the merged pull request that first added it, read from the site's history rather than stored.
This holds only while the site's `main` changes through accepted pull requests alone, so a maintenance change made any other way would claim every certificate it touches.

Pages and badges are built by the site from submitted scores and never committed, so no author-written HTML is served from the shared origin.

One certificate covers one repository.
Work spanning several gets one certificate each, never merged by hand.

The tool never writes a score into a commit, a pull request or a file.
It prints text to paste, because where a score goes is the author's decision.

A private repository publishes its identifier and nothing else, so the page withholds repository and branch names.

## This tool scores its own construction

It was built across three milestones, and each slice was scored by the tool as it went.
Findings about this repository are expected rather than embarrassing, and two are standing: the subprocess calls in `git_repository.py` and `risk.py` are genuine, and the commit history says "non-generative" where the code says "deterministic".

Its last certificate, `https://vibecert.github.io/bcf81d7`, predates `vibecert/certificate@2` and the normalised identifier, so it must be rescored.

## Working here

The author stages work in topical slices and will ask for one concern at a time, sometimes across parts of files.
Build the intended state in the scratch directory first, verify it there as a standalone tree, then stage, then restore the full worktree.
A staged state that was never run is not worth staging.

Commits follow Angular conventions with a `(vibecert)` scope, and a squash commit's body lists its sub-branch's commits in chronological order, not the parent branch's.

## Gotchas

These each cost real time to find.

`ruff format` reflows code, so a scripted string replacement written against the pre-format text silently matches nothing.
Assert the replacement count.

`gh` prints a 404 body to standard output, so `sha=$(gh api ...)` captures JSON rather than nothing.
Reset it with `|| sha=""`.

This shell is zsh, which does not word-split `${sha:+-f sha="$sha"}`, so `gh` receives one argument and returns 422.
Pass such arguments through an array.

`/usr/bin` is not on this shell's PATH, so call `gh` and `base64` by absolute path.

`~/.claude/skills` is a symlink to this repository, so session directories and edit paths must be resolved before comparing them to a repository root.

A session belongs to a repository if its working directory or any file it edited lies inside it, and only edits inside the repository are counted.
Matching on working directory alone missed work done in a second repository by `cd` from a session started in the first.

Inline `$(base64 ...)` on a backslash-continued `gh api` line breaks in zsh, with "command not found" for it and later commands.
Write the encoding to a scratch file and pass it with `-F content=@<file>`.

In auto mode a looped `gh api` read is refused even though it is read-only, so verify a push with one `curl` against the raw file.

Git emits timestamps as `+01:00` and transcripts emit `Z`, so compare them as instants rather than strings.

In auto mode there are no `Edit` or `Write` tool calls at all; edits arrive as `bashEditDiff` on a `Bash` result.
`file-history-snapshot` entries are usually empty and are not used.

Formatter runs dominate edit counts, 87 of 119 on one branch, which is why revisions exclude them.

A certificate's identifier is a hash of remote, branch and merge base, with a GitHub remote reduced to its owner and name, so rescoring a branch replaces its certificate rather than adding one.

Shields caches a badge for 300 seconds and GitHub proxies it again, so a rescored badge lags even though the page updates at once.

## Known limitations

The certificate does not discriminate on this repository.
Five branches scored near-identically, because the weight is pinned at 3 by criticality and two of the three deterministic metrics are constant here.
A real spread test needs another repository.

Metric 1 has never been run twice, so the variance of the judged half is unmeasured, and that half carries almost all the discrimination.

Fan-in is quadratic in file count, fine at 46 files and slow at thousands.
Risk findings come from ruff, so only Python is covered.
Whether checks ran is detected repository-wide rather than scoped to the changed files.
A session that worked across two repositories contributes all its prompts and tool calls to both, since a prompt is not tied to a repository.
Sensitive-data matching strips quotes and comments per line, so a term inside a multi-line docstring still matches.

## Verifying

From `scripts`: `uv run ruff format .`, `uv run ruff check .`, `uv run ty check .`, then `uv run pytest -q --cov --cov-report= --cov-fail-under=80`.
Run all four after any change.
