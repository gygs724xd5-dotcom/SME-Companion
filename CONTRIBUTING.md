# Contributing

This project is currently optimized for focused product sprints. Keep changes small, verify the Streamlit experience locally, and update documentation when product behavior changes.

## Developer Workflow

1. Create a branch for the sprint or fix.
2. Inspect the current Streamlit flow before changing behavior.
3. Keep documentation-only work separate from application logic changes.
4. Make the smallest change that satisfies the product objective.
5. Run local verification.
6. Update version notes when behavior changes.
7. Review changed files before committing.

## Branch Strategy

| Branch type | Naming example | Use |
| --- | --- | --- |
| Feature | `feature/product-brain-summary` | New product capability. |
| Fix | `fix/demo-fallback-copy` | Bug fix or reliability improvement. |
| Docs | `docs/project-documentation` | Documentation-only changes. |
| Release | `release/v2.0.0` | Release preparation and final verification. |

## Commit Naming

Use concise, conventional-style commit names:

```text
docs: add project documentation
feat: add product feedback prioritization
fix: handle missing provider key fallback
chore: update deployment checklist
```

## Versioning

SME Companion uses semantic product milestones:

| Version type | Meaning |
| --- | --- |
| Major | Foundation-level shift in product architecture or product scope. |
| Minor | New user-visible capability or major sprint milestone. |
| Patch | Focused improvement, bug fix, or small capability extension. |
| RC | Release-candidate validation before a stable milestone. |

Update [CHANGELOG.md](CHANGELOG.md) for each release-level change.

## Testing Checklist

Before merging application changes:

- Run `streamlit run app.py`.
- Confirm the app starts without provider keys.
- Confirm the configured LLM provider works when keys are available.
- Confirm demo store selection loads each demo profile.
- Confirm manual store setup still works.
- Confirm generated content and sales brief views render.
- Confirm chat handles business questions.
- Confirm chat handles product feedback without requiring an LLM call.
- Confirm feedback summary renders when feedback exists.
- Confirm local JSON writes are expected and limited to runtime data.

## Documentation Checklist

For documentation-only changes:

- Do not modify Python files.
- Keep claims aligned with current code.
- Avoid describing planned features as already shipped.
- Update links between README, roadmap, architecture, changelog, and sprint history.
- Run `git status --short` before final review.

## Deployment Checklist

Before Streamlit deployment:

- Confirm `requirements.txt` includes required runtime packages.
- Confirm `app.py` is the configured Streamlit entry point.
- Add Streamlit secrets for provider keys as needed.
- Configure `APP_ENV`, `LLM_PROVIDER`, and model overrides if required.
- Smoke test demo mode.
- Smoke test chat fallback behavior with missing provider keys.
- Smoke test product feedback capture.
- Review LLM usage and budget guard behavior.

## Pull Request Checklist

- Scope is clear and limited.
- Changed files match the stated sprint objective.
- Product behavior changes are reflected in `CHANGELOG.md`.
- Roadmap or sprint history is updated when a milestone changes.
- No unrelated files are reformatted or reverted.
