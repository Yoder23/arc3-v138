# ARC-AGI-3 V138: retained learning and bounded planning

V138 is an observation-driven puzzle agent developed by **Yoder23** with AI-assisted research and implementation. It learns control effects during play, tests hypotheses, retains failed attempts, and combines preserved specialists with bounded planning. This repository releases the exact policy used in the frozen V138 candidate and explains both the measured gains and the limitations.

**Local adaptive public result: 76.99252294322464 / 100 RHAE, 153 / 183 levels, 16 / 25 complete games.** The final full-suite validation executed 7,585 fresh environment actions with zero cached policy responses. This is a local public result, not a Kaggle leaderboard result or a held-out generalization claim.

At release preparation, the author reported that Kaggle Save & Run All completed. Its hosted logs have not been independently audited, and the competition submission has not yet been made. Hidden performance and leaderboard rank are unknown.

## Start here

| Item | Location |
| --- | --- |
| Readable agent and driver: 558 Python files | [src/](src/) |
| Exact compact Kaggle notebook, 959,128 bytes | [submission/submission.ipynb](submission/submission.ipynb) |
| Full research write-up | [Research report](docs/RESEARCH_REPORT.md) |
| Polished 15-page report | [PDF](docs/report/ARC3-Research-and-Submission-Report-V138.pdf) |
| Integrity, build and execution instructions | [Reproducing V138](docs/REPRODUCING.md) |
| Original validation summaries and exact pins | [submission/](submission/) |
| Project license | [MIT-0](LICENSE) and [license scope](LICENSE-SCOPE.md) |
| Dependencies and acknowledgements | [Third-party notices](THIRD_PARTY_NOTICES.md) |

## How the agent works

1. The driver provides image frames, animation frames, available actions, game state, and level progress. The policy does not receive game identifiers.
2. Scene-based admission routes observations to retained specialists or preserved parent behavior.
3. Specialists infer control mappings, geometry, temporal changes and intermediate goals from observations.
4. Bounded probes and plans test predictions. Contradictions revise hypotheses; supported rules can transfer to later levels in the same game.
5. Research changes were qualified with fresh replay, parent-preservation checks and complete uncached public evaluation.

The final selective policy is CPU-based. Optional neural research code remains in the source dependency closure, but Torch was blocked during qualification and no LLM calls were used in this phase. The result does not establish brain emulation, subjective emotion, a neural-cell advantage, or a general-purpose scientist. The report describes the earlier spiking and liquid-inspired experiments and their negative controls.

## Verify the release

Python 3.10 or newer suffices for the standard-library integrity check:

```console
python -B scripts/verify_release.py
```

For a zero-action initialization check with NumPy and SciPy installed:

```console
python -B submission/verify_local.py --check-only --policy-python python --output local-check
```

Use a new output directory each time. Full public evaluation also requires the official SDK and a separately obtained public environment bundle. See [reproduction instructions](docs/REPRODUCING.md). Benchmark environments, response traces, answer files, trained weights, private credentials and dependency distributions are not included.

## Submission identity

The compact notebook embeds the same ZIP as `submission/policy-package.zip`. Every file extracted under `src/` is byte-identical to that ZIP. The size fix changed only the notebook transport encoding; it did not change the policy.

| Artifact | SHA-256 |
| --- | --- |
| Compact notebook | `bda7e4e4d87f0ce5ebb315d794e4c0e99f2738afaddb2eb5483f8da101199b94` |
| Frozen policy ZIP | `b992030ca9dad1998af5f7612f196fa68b58b08c3c40a87411d1c1cbc81623cb` |
| Original full-suite validation record | `137655f56da5a714408e77c8429baae1025b511df4133499e1bbdc0874348774` |

The historical build manifest inside the ZIP predates validation and license selection. [LICENSE-SCOPE.md](LICENSE-SCOPE.md) records the MIT-0 release grant; [PACKAGING-CORRECTION.txt](submission/PACKAGING-CORRECTION.txt) explains the compact notebook hash. Original historical records remain unchanged.

## Evaluation limits and licensing

Public games were used adaptively during development. Scene-specific routing can overfit those families. A high local score cannot establish a hidden score, a leaderboard position, or prize eligibility. V139 is not included because its full-suite qualification did not finish.

Project-authored code, methods as documented, and documentation are released under **MIT No Attribution (MIT-0)**. Third-party libraries retain their own licenses and are supplied separately. Publishing this repository addresses the public source-release requirement; the organizers determine eligibility under the full competition rules.

Reference: [ARC Prize 2026 rules](https://arcprize.org/competitions/2026), [ARC submission workflow](https://docs.arcprize.org/arc-prize-2026).
