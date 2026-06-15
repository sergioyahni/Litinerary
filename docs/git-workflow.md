# Git Workflow

Litinerary uses Git for local project history. Keep commits small, readable, and free of secrets or generated artifacts.

## Check Status

```bash
git status
git branch --show-current
git remote -v
```

Use `git status --short` when you want a compact view before staging.

## Create a Feature Branch

```bash
git switch -c feature/short-description
```

Prefer a short branch name that describes the work, such as `feature/narration-foundation` or `chore/git-hygiene`.

## Commit Safely

Review changes before staging:

```bash
git diff
git status --short
```

Stage only intentional project files:

```bash
git add <path>
git diff --cached
git commit -m "type: concise summary"
```

Do not stage local databases, generated builds, caches, virtual environments, logs, or private environment files.

## Secrets Policy

Never commit secrets, API keys, tokens, real provider credentials, local databases, or private `.env` files.

`.env.example` is safe to commit because it contains placeholders and documents expected configuration. `.env`, `.env.local`, and other local environment files are private and ignored.

## Commit Message Style

Use concise conventional-style messages:

- `feat: add itinerary narration UI`
- `fix: handle missing itinerary narration`
- `chore: update repository hygiene`
- `docs: document provider setup`
- `test: cover mock narration service`

Keep the subject line imperative and specific. Add a body when the change needs context, tradeoffs, or rollout notes.

## Remote Setup

Check configured remotes:

```bash
git remote -v
```

If no remote is configured, add one later with:

```bash
git remote add origin <remote-url>
```

Do not push until the remote is confirmed and the intended branch is reviewed.
