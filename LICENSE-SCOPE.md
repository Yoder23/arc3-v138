# License scope

The root [LICENSE](LICENSE) grants **MIT No Attribution (SPDX: MIT-0)** for project-authored code and associated documentation in this release, including `src/`, `scripts/`, the project-authored contents of the embedded policy archive and notebook, the report, and the documented methods. Copyright holder: Yoder23, 2026. This license choice is made for the public V138 release at the author's request.

MIT-0 is one of the license examples named in the [ARC Prize 2026 rules](https://arcprize.org/competitions/2026). It permits use, modification, distribution, sublicensing and sale without an attribution condition; it supplies no warranty. See the [SPDX reference](https://spdx.org/licenses/MIT-0.html).

This grant does not relicense third-party software, benchmark environments, third-party trademarks, or any other material the author does not own. Runtime dependencies are distributed separately under their upstream terms. The notices under `LICENSES/` preserve relevant upstream license texts; they are not project-authored MIT-0 material.

## Preserving frozen artifacts

`src/MANIFEST.json` and the same historical manifest embedded in `submission/policy-package.zip` say license selection was pending. That records the state when V138 was frozen, before this public release. **The root LICENSE and this scope document supply the release license for the project-authored contents identified by `RELEASE-MANIFEST.json`.** No policy or notebook bytes were rewritten to update historical metadata. This also preserves the exact source used in local validation and uploaded by the author.

The original report is preserved as a dated research record. Later packaging and publication status are described in the repository README and release notes.

## Authorship and provenance

The release contains 558 project Python files. Each matched the frozen ZIP and the retained workspace source path recorded by its manifest. Source headers were inspected for existing copyright/license and copied-source notices; no conflicting source notice was found. The project used AI assistance for research, implementation and documentation. This is a source/provenance inventory, not a claim of independent third-party legal certification.

Public SDKs and the ARC Kaggle starter informed interface usage. The starter's deployment contract was referenced at commit `eeb1535404f321d280a8f9194bbc1d7aca5f05fc`; its repository files are not vendored here. The supplied OHGW bridge and other reviewed research repositories are not V138 runtime dependencies and their source trees are not included. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
