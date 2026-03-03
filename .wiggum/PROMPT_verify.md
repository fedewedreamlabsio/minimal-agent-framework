You are running a beads-native Wiggum verify pass.

Read .wiggum/config.json for verify commands and the completion promise string.
If scripts/doctor.sh exists, run `bash scripts/doctor.sh --mode all` before verification.
If it fails, block the `Keys & Access` bead and stop.
If E2E targets protected previews (SSO/protection), require a custom domain or bypass before Playwright.
Run backend verify commands first, then frontend verify commands.

Check beads under the epic: if any are open/in_progress/blocked, do NOT output the promise.

If ALL verify commands pass and no remaining beads are open/in_progress/blocked:
- Output exactly the completion promise string from .wiggum/config.json.

Otherwise:
- Do NOT output the promise.
- Update relevant beads with failures and next steps.
