V138 COMPACT PACKAGING CORRECTION
Use submission.ipynb from THIS compact folder. Replace the previous notebook rather than appending cells.
Notebook: 959,128 bytes; all cell sources: 958,369 bytes; both below 1,000,000.
No separate dataset is needed. Kaggle acceptance and execution still require confirmation there.

ARC-AGI-3: SUBMIT V138

READY FOR YOUR UPLOAD
This compact notebook changes only the embedded ZIP encoding to fit the Kaggle source limit. The decoded policy ZIP is byte-for-byte identical to the fully validated V138 candidate. Local public RHAE: 76.99252294322464/100; 153/183 levels; 16/25 complete wins; 7,585 fresh actions; zero cached responses. Kaggle/Linux initialization, official hardware and hidden performance are still unverified.

SUBMIT THROUGH THE KAGGLE WEBSITE
1. Extract this archive. In your entered ARC Prize 2026 ARC-AGI-3 competition, create/import a private notebook using submission.ipynb. Upload the notebook file, not this ZIP. The policy is embedded; no separate policy dataset or weights upload is needed.
2. Attach the competition data (arc-prize-2026-arc-agi-3), select CPU and keep Internet OFF. The notebook installs official wheels offline from /kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels and requires NumPy/SciPy in the runtime.
3. Save Version / Save & Run All. Check that all cells succeed and the log says "Policy initialization passed. This is not a benchmark score." Check that /kaggle/working/submission.parquet is present. If initialization fails, fix that failure before submitting; local verification does not establish hosted compatibility.
4. Use the competition submission workflow to select this saved notebook version and submission.parquet. The ordinary notebook run creates only an UNSCORED SCHEMA FIXTURE. During the competition rerun, KAGGLE_IS_COMPETITION_RERUN activates the agent, which waits for the official gateway and plays the evaluated games. The gateway produces the real submission result. Do not interpret the fixture as an evaluated score.
5. Confirm on Kaggle that the competition submission finishes successfully and inspect the result there. This handoff has not uploaded or submitted anything for you.

The metadata template is optional for website upload. If using Kaggle CLI instead, replace REPLACE_WITH_YOUR_KAGGLE_HANDLE in kernel-metadata.template.json and save your configured copy as kernel-metadata.json. Preserve this frozen handoff.

WHAT IS INCLUDED
submission.ipynb: upload this; the policy source is embedded and SHA-256 checked.
policy-package.zip: identical, separately inspectable policy source.
requirements.txt: dependency requirements; official wheels/runtime supply dependencies.
kernel-metadata.template.json: optional private CPU/Internet-OFF configuration.
READINESS.json and VALIDATION-SUMMARY.json: measured local results and limits.
RUNTIME-PINS.json: exact local Windows interpreter/package metadata, not a claim of Linux compatibility.
verify_local.py: standalone integrity and local initialization/reproduction tool.
CHECKSUMS.json: SHA-256 hashes and byte counts for the handoff files.

No benchmark traces, cached responses, game implementations, credentials, answer files or large model weights are included. V139 is excluded because its full-suite validation failed when disk space was exhausted. V138 and older candidates and all retained research knowledge remain preserved locally.

OPTIONAL LOCAL CHECK (ZERO GAME ACTIONS)
Use a Python interpreter with NumPy and SciPy; choose a new empty output path:
python verify_local.py --check-only --policy-python PATH_TO_PYTHON_WITH_NUMPY_SCIPY --output NEW_CHECK_DIRECTORY

OPTIONAL FRESH LOCAL PUBLIC EVALUATION
With the official arc-agi SDK and an existing public environment bundle supplied separately:
python verify_local.py --policy-python PATH_TO_PYTHON_WITH_NUMPY_SCIPY --environments PATH_TO_EXISTING_PUBLIC_BUNDLE --output NEW_RUN_DIRECTORY
Add --sdk-path PATH_TO_SDK if the SDK is an existing source directory. No downloads are performed. This is not required to upload the V138 policy in this compact notebook.

DEPLOYMENT EVIDENCE
The official starter deployment contract was checked at commit eeb1535404f321d280a8f9194bbc1d7aca5f05fc. Its README and scripts/build_notebook.py describe commit/rerun separation and offline wheels. Platform requirements and hidden results must be confirmed on Kaggle.
Agent limits: 1,024 actions/game; 600 wall seconds/game; 28,800 internal run seconds; guarded policy 600 CPU seconds and 2 GiB. No LLM calls are used in this candidate phase.

Research was stopped at the user's request for immediate handoff. The scheduled research automation was deleted. Nothing was uploaded, published or submitted by the assistant.
