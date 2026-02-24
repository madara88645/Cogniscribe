# Conflict-Aware Branch Merge Skill

Use this skill when you want GitHub Copilot Chat (or a similar coding agent) to
merge branches **with conflicts**, while obeying a policy you provide.

## Goal

- Understand the codebase and intent on both branches.
- Resolve conflicts in a way that matches the user's merge policy.
- Produce a clean, reviewable merge with verification steps.

## Inputs you must request (ask max 3 questions if missing)

1. **Merge direction** — which branch merges into which:
   - `"merge <source> into <target>"`, e.g. `"merge feature/login into main"`
2. **Conflict-resolution policy** — how to handle ambiguous conflicts, e.g.:
   - `"prefer target"` — keep the target-branch version when in doubt
   - `"prefer source"` — keep the source-branch version when in doubt
   - `"ask per conflict"` — pause and ask the user for each conflict
   - `"combine both"` — attempt to incorporate both sides where safe
3. **Verification command** *(optional)* — what to run after the merge to
   confirm success, e.g. `"pytest -q"` or `"npm test"`.

## Step-by-step procedure

### 1 — Gather context

```
git log --oneline <target>..<source>   # commits unique to source
git log --oneline <source>..<target>   # commits unique to target
git diff <target>...<source>           # three-dot diff (common ancestor)
```

Read the diff and commit messages to understand **intent** on each branch.

### 2 — Identify conflicts

```
git merge --no-commit --no-ff <source>
git diff --name-only --diff-filter=U   # list conflicting files
```

For each conflicted file, read the conflict markers (`<<<<<<<`, `=======`,
`>>>>>>>`) and classify each hunk as one of:

| Type | Description |
|------|-------------|
| **Safe-take-source** | Target has no meaningful change; source is clearly correct. |
| **Safe-take-target** | Source change is superseded or reverted by target. |
| **Combine** | Both sides add non-overlapping functionality. |
| **Ambiguous** | Semantically conflicting; policy or human decision required. |

### 3 — Resolve conflicts

Apply the user's policy:

- **`prefer target`** → for *Ambiguous* hunks, keep the target version.
- **`prefer source`** → for *Ambiguous* hunks, keep the source version.
- **`ask per conflict`** → show both sides and wait for the user to choose.
- **`combine both`** → merge both sides, ensuring no duplicate logic.

After editing each file, remove all conflict markers (`<<<<<<<`, `=======`,
`>>>>>>>`). Verify with:

```
grep -rn "<<<<<<\|=======\|>>>>>>>" .
```

### 4 — Stage and verify

```
git add <resolved-files>
```

Run the verification command supplied by the user (or the project's default
test/build command). Fix any failures before proceeding.

### 5 — Commit the merge

```
git commit -m "Merge <source> into <target>

Conflict resolution policy: <policy>

Resolved conflicts in:
  - <file1>: <brief rationale>
  - <file2>: <brief rationale>"
```

### 6 — Post-merge checklist

- [ ] All conflict markers removed.
- [ ] Verification command exits 0.
- [ ] No unintended deletions — check `git diff <target>` for surprises.
- [ ] Commit message documents the policy and rationale.

## Example interaction

> **User:** Merge `feature/audio-upgrade` into `main`. Prefer source on
> conflicts. Run `pytest -q` to verify.

The agent will:
1. Fetch intent from both branches.
2. Run `git merge --no-commit --no-ff feature/audio-upgrade`.
3. Resolve each conflict by taking the `feature/audio-upgrade` (source) side
   for ambiguous hunks.
4. Run `pytest -q`; fix failures if any.
5. Commit with a message that records the policy and per-file rationale.
