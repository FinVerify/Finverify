# Legacy SDK Prototype (Archived)

This directory contains the original hand-written SDK prototype for FinVerify. It has been **superseded** by the standalone [`finverify-sdk/`](../../finverify-sdk/) package, which is the version published to PyPI as `pip install finverify-sdk` and tested in CI.

This directory is kept because [`finverify-sdk/CHANGELOG.md`](../../finverify-sdk/CHANGELOG.md) and [`finverify-sdk/docs/architecture.md`](../../finverify-sdk/docs/architecture.md) reference it as the historical origin of the vendored DVL and normalizer code (`finverify/{dvl,normalizer}.py`).

**Do not:**
- Import from this directory in new code
- Rely on it being tested by CI (it is not)
- Treat it as the current SDK — use `finverify-sdk/` instead
