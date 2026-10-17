# VibeCert

Collects the evidence a branch is scored from: its diff, the Claude Code sessions that produced it, and which of its lines the model wrote.

## Usage

```
uv run vibecert --repo <path> --out <bundle.json>
```

`--base` names the branch to compare against, defaulting to the conventional default branches in turn.
`--untracked` counts files Git is not tracking, which are excluded otherwise.

The site runs two more commands.
`vibecert-accept <submission> --submitter <id> --site-url <site> --changed <path>...` checks a pull request to the site.
`vibecert-build <source> <out>` builds every certificate's page and badge from the submitted scores.

## Requiring a certificate

`vibecert-verify` fails a pull request whose branch has no current certificate, or one scoring below `--threshold`.
It must run on the pull request's own head with full history, since `actions/checkout` otherwise checks out a merge commit.

```yaml
on: pull_request
jobs:
  vibecert:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          ref: ${{ github.event.pull_request.head.sha }}
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v6
      - run: >-
          uvx --from "git+https://github.com/martinchapman/claude-skills#subdirectory=vibecert/scripts"
          vibecert-verify --branch "$GITHUB_HEAD_REF" --base "origin/$GITHUB_BASE_REF"
          --site-url https://vibecert.github.io --threshold 2
```
