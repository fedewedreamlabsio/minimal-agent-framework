You are running a beads-native Wiggum planning pass.

Read PRD.md, .wiggum/config.json, and existing beads.
Do NOT change code. You may create/update beads and update .wiggum/config.json if needed.

Rules:
- If PRD.md is missing or lacks prerequisites, stop and ask to run the PRD skill first.
- If beads is not initialized, stop and ask to run `bd init`.
- Tasks should be 45-90 minutes each. Split anything larger.

Process:
1) Determine the epic id:
   - Use .wiggum/config.json beads.parent if set.
   - Else parse the PRD title for the project name and search epics with `bd list --type epic --title-contains <name> --json`.
   - If none exist, create one: `bd create --type epic --title "PRD: <name>" --description <summary> --labels wiggum`.
   - If created, update .wiggum/config.json beads.parent with the new epic id.
2) Create or update a `Keys & Access` bead (type task) under the epic.
   - Include CLI/tooling, tokens, Playwright deps, and preview/E2E access constraints (SSO/protection, custom domain, bypass).
3) Map PRD sections to feature/task beads under the epic.
4) Add acceptance criteria and dependencies (bd dep add), including making all beads depend on `Keys & Access`.
5) Apply labels from config (beads.label_all) plus area labels when obvious.

Output:
1) Summary of beads created/updated (IDs)
2) Confirmation that no code was changed
