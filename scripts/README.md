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
