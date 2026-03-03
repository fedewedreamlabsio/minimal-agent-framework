# Wiggum Operations

## Beads
- Ready: bd ready --parent <EPIC_ID>
- List: bd list --parent <EPIC_ID>
- Show: bd show <BEAD_ID>
- Claim: bd update <BEAD_ID> --claim --status in_progress
- Close: bd update <BEAD_ID> --status closed --notes "tests: ...; commit: ..."

## Preflight
- Doctor: bash scripts/doctor.sh --mode all
- Provision: bash scripts/provision.sh (if present)

## Standard Kit
- CLIs: git, node, pnpm, bd, vercel, railway, python3
- Logins: vercel whoami --token $VERCEL_TOKEN; railway whoami
- Playwright browsers: pnpm -C apps/web exec playwright install
- E2E access: preview must be public or use a custom domain/bypass if SSO/protection is enabled

## Tests
- Backend: TODO (no backend detected)
- Frontend: TODO (no frontend detected)

## Lint/Typecheck
- Backend: TODO
- Frontend: TODO (no frontend detected)

## Run
- Backend: TODO
- Frontend: TODO
