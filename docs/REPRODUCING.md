# Reproducing the frozen V138 release

## Integrity (no dependencies, downloads or game actions)

Run from the repository root with Python 3.10+:

```console
python -B scripts/verify_release.py
python -B scripts/rebuild_submission.py --output local-build
```

The verifier checks all release-file hashes, the decoded notebook payload, the archive manifest, all 558 source files, and notebook/source syntax. The rebuild reads the visible `src/` files, preserves original ZIP entry metadata, and requires its ZIP and compact notebook to match the frozen SHA-256 values. It refuses to overwrite an output directory. It does not change or upload the submission.

## Policy initialization (zero game actions)

Use an interpreter with NumPy and SciPy. The original Windows qualification used Python 3.10.0, NumPy 2.2.6 and SciPy 1.15.3 for the policy; its coordinator was Python 3.12.14. The official SDK requires Python 3.12. See `submission/RUNTIME-PINS.json` for the exact historical metadata.

```console
python -B submission/verify_local.py --check-only --policy-python python --output local-check
```

If using different coordinator and policy interpreters, replace the first `python` with the coordinator path and `--policy-python python` with the full policy interpreter path. Success produces `local-check/VERIFICATION.json` with `source_hashes_verified` and `policy_initialized` true and `new_environment_actions` zero.

## Fresh local public evaluation

Install or supply the official `arc-agi` SDK and its dependencies separately. The measured SDK versions were arc-agi 0.9.9 and arcengine 0.9.3. The policy dependencies above were pinned for the historical result. The release does not redistribute dependency wheels or benchmark implementations. Supply an existing official public environment bundle obtained through the authorized competition distribution:

```console
python -B submission/verify_local.py --policy-python python --environments /path/to/public-bundle --output local-evaluation
```

Add `--sdk-path /path/to/sdk-import-root` if the SDK is supplied from an existing local import directory. Use Python 3.12 for the coordinator. This run interacts through the official offline interface; it does not read reference responses. It can take substantial time, uses 1,024 actions/game and a 600-second per-game wall budget, and writes local output files. Outputs are excluded by `.gitignore`.

The measured reference is 25 games, 153/183 levels, 16 wins, 7,585 fresh actions, zero cached responses, and RHAE 76.99252294322464. Different environment versions, dependencies or hardware can change the outcome. The verifier asserts agreement and leaves failure evidence if the run differs. Do not call a failed reproduction a pass.

## Kaggle

Use `submission/submission.ipynb` unchanged, attach ARC Prize 2026 ARC-AGI-3 competition data, select CPU and disable Internet. The notebook installs official SDK wheels from the mounted competition data. NumPy, SciPy, pandas and a pandas-compatible Parquet engine must be available in the hosted runtime. Its ordinary saved run initializes the policy and emits an explicitly unscored schema fixture. A separate competition submission triggers the gateway run and real output.

The author reported Save & Run All completed before this release was prepared. No hosted logs, hardware behavior, official score or hidden performance have been independently verified here. The Kaggle competition submission is still pending. Publishing a GitHub repository does not submit to Kaggle.

The driver uses the official competition gateway's fixed `test-key-123` test value. This is not a private API credential. Do not add private keys, game code, evaluation traces or account tokens to the repository.
