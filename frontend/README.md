# AEGISCORE AI Flutter frontend

The app supports two explicit repository modes:

- **Demo fixture mode** (default): renders synthetic offline fixtures and does not contact the backend.
- **Live backend mode**: calls only the existing `GET /health` and `GET /capabilities` FastAPI endpoints. Other screens show unsupported states because their backend contracts do not exist. There is no automatic demo fallback.

See [`docs/PHASE_8G3_API_INTEGRATION.md`](../docs/PHASE_8G3_API_INTEGRATION.md) for run commands, configuration, field mapping, screen coverage, and limitations.

## Verify

```powershell
flutter analyze
flutter test
```
