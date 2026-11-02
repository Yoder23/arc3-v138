# Third-party notices and acknowledgements

The project MIT-0 grant applies to project-authored material. External libraries retain their own licenses. No third-party Python distributions, wheel files, trained weights or benchmark environment implementations are bundled. License texts are preserved below for transparency; installing dependencies requires their original licenses and bundled-component notices.

| Component | Inspected version | Upstream license | Role |
| --- | --- | --- | --- |
| [arc-agi](https://pypi.org/project/arc-agi/0.9.9/) | 0.9.9 | [MIT](LICENSES/arc-agi.txt) | Official API client; installed separately. |
| [arcengine](https://pypi.org/project/arcengine/0.9.3/) | 0.9.3 | [MIT](LICENSES/arcengine.txt) | Official action types and local engine; installed separately. |
| [python-dotenv](https://pypi.org/project/python-dotenv/1.2.4/) | 1.2.4 | [BSD-3-Clause](LICENSES/python-dotenv.txt) | SDK environment loading; installed separately. |
| [numpy](https://pypi.org/project/numpy/2.2.6/) | 2.2.6 | [BSD-3-Clause](LICENSES/numpy.txt) | Policy arrays and numerics; installed separately. |
| [scipy](https://pypi.org/project/scipy/1.15.3/) | 1.15.3 | [BSD-3-Clause](LICENSES/scipy.txt) | Policy image/object operations; installed separately. |
| [torch](https://pypi.org/project/torch/2.7.1/) | 2.7.1+cu118 | [BSD-3-Clause](LICENSES/torch-0.txt) | Optional inactive research arm. Not required by the qualified selective policy. |
| [pandas](https://pypi.org/project/pandas/3.0.1/) | 3.0.1 | [BSD-3-Clause](LICENSES/pandas.txt) | Notebook commit-mode Parquet fixture; installed separately; hosted version not recorded. |

NumPy, SciPy and Torch distribution notices can cover multiple bundled native components. The full locally supplied notices are retained rather than relabeling those components under the headline license. The exact Kaggle runtime versions, including its Parquet engine, remain unrecorded; this repository does not distribute those binaries.

The official ARC SDK and [Kaggle starter](https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter/tree/eeb1535404f321d280a8f9194bbc1d7aca5f05fc) informed public interface and gateway conventions. The pinned starter tree has no root license file; its source files are not vendored in this repository. The release contains the project-authored driver and notebook wrapper, not a copy of the starter repository.

The author-supplied OHGW bridge was reviewed during research as a separate diagnostic tool under its Apache-2.0 notice. It is not a dependency of the frozen V138 policy and is not redistributed here. Other reviewed research repositories, datasets and benchmark implementations are also outside the release.

The gateway string `test-key-123` in `src/client.py` is the public competition test value, not a private account credential. No user API key or account token is included.

Dependency metadata provenance and notice paths are recorded in [DEPENDENCIES.json](DEPENDENCIES.json). This inventory describes the release contents; it does not assert an audited license inventory of every hosted runtime transitive dependency.
