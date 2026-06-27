# Changelog

## 2026-06-27

### Added

- Planner-first response intelligence layer.
- Response guard and repetition guard.
- Missing information collector for workflow fields.
- Business context memory sync from task route to session/application state.
- Owner login/logout foundation with local salted password hashes.
- Owner-scoped manual store persistence.
- OCR/inventory foundation module without fake OCR.
- Translation request foundation for Thai, English, Arabic, and Chinese.
- Production documentation set.

### Changed

- Planner output now includes selected `workflow`.
- Chat assistant messages use a minimal black indicator and stream new responses.
- Infrequently used store sections moved into sidebar expanders.

### Security

- Anonymous sessions no longer restore the previous manual store.
