# Runbook

**Weaver Forge — Daily Commit Lab**

This runbook explains how to check that the repository is launch-ready.

## Local readiness check

Run this from the repository root:

```bash
python scripts/check_repo.py
```

Expected result:

```text
PASS: Weaver Forge repository readiness checks passed.
```

## What the readiness check verifies

- All required launch files exist.
- Required files are not empty.
- Markdown files are valid UTF-8 and end with a newline.
- The README contains the project title, motto, secondary law, and Discord invite.
- Internal Markdown links resolve to real repository files.
- Old launch placeholders are not left in public docs.
- Template placeholders stay inside the receipt and witness templates.

## GitHub Actions

The `Repo Readiness` workflow runs automatically on:

- Pushes to the repository
- Pull requests
- Manual workflow dispatch

## Manual launch checklist

- [ ] Confirm the Discord invite is active.
- [ ] Enable GitHub Discussions if the community will use Discussions.
- [ ] Open the first Build Receipt issue or project thread.
- [ ] Ask one independent reviewer to attempt the witness template.
- [ ] Keep all claims tied to commits, receipts, or witness reviews.

---

**Build. Test. Commit. Receipt. Repeat.**
