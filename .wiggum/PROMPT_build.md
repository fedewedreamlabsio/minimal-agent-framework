You are running a beads-native Wiggum build pass.

Read PRD.md, .wiggum/config.json, and existing beads.
Use beads as the source of truth for work.

Process:
1) Determine the epic id (config beads.parent).
2) If scripts/doctor.sh exists, run `bash scripts/doctor.sh --mode all`.
   - If it fails, find or create the `Keys & Access` bead, set it to blocked with the missing items, and stop.
3) If scripts/provision.sh exists and the bead involves deploy/E2E, run it and source .tmp/provision.env.
4) If any in_progress bead exists under the epic, resume it.
   Otherwise pick the top ready bead: `bd ready --parent <epic> --sort hybrid --limit 1`.
5) Claim the bead: `bd update <id> --claim --status in_progress`.
6) Implement the change, add automated tests when feasible.
7) Run targeted tests for the change.
8) Commit per bead: `<id>: <summary>` (include .beads/issues.jsonl updates).
9) Close the bead: `bd update <id> --status closed --notes "tests: <cmds>; commit: <hash>"`.

Rules:
- Do not start a new bead on a dirty working tree.
- If blocked, set status blocked with clear notes and create follow-up beads if needed.
- Do NOT push to git remotes.

Output:
- Bead id, summary of changes, tests run, commit hash, and new status.
