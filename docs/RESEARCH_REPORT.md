# ARC AGI 3 Research and Submission Report

> Historical report dated 2026-11-02. The PDF and underlying report content are preserved unchanged. The current README records later compact packaging, licensing and publication status. Source IDs below refer to the retained local research archive; that archive is not redistributed. The evidence index supplies provenance hashes, not publicly hosted copies of every experiment.

[Download the polished PDF](report/ARC3-Research-and-Submission-Report-V138.pdf) · [Evidence index](report/evidence-index.json)

## ARC AGI 3 Research and Submission Report

Retained learning and validated public performance for V138

November 2 2026 | Research closeout and submission companion

### Executive summary

We developed an interactive puzzle-solving system around a repeated cycle of observation, hypothesis formation, action, failure analysis and retained knowledge. The strongest completed candidate is V138. It achieved 76.9925 out of 100 on the local public ARC-AGI-3 evaluation, completing 153 of 183 levels and winning 16 of 25 games. The final validation executed 7,585 fresh actions with zero cached policy responses. [S01]

| Measure | Verified result |
| --- | --- |
| Local public RHAE | 76.9925 / 100 |
| Completed levels | 153 / 183  \|  83.61% |
| Complete game wins | 16 / 25  \|  64.00% |
| Fresh validation actions | 7,585 |
| Cached policy responses | 0 |
| Kaggle and hidden evaluation | Unverified |

The engineering contribution is a portfolio of observation-driven controllers with retained evidence, bounded planning and explicit checks that new behavior preserves earlier skills. Public gains were accepted through fresh replay, evidence audits and complete uncached evaluation. The score is a local action-efficiency measure; it is neither the fraction of levels completed nor the fraction of games won. [S01, S08, S12]

The original research direction emphasized human-like learning, associative memory and neuromorphic mechanisms. Early experiments implemented and compared neural variants. Those controls did not establish a general advantage for spiking or liquid-inspired models. The final result should be attributed to the tested system as a whole, with its concrete memory and planning mechanisms, rather than to a claim of brain emulation. [S03-S07]

### Delivery decision

V138 is frozen and packaged for the user to upload. V139 remains research-only because its full 25-game validation failed when disk space was exhausted. The user requested immediate packaging; research was stopped and its scheduled automation deleted. No upload, hosted run, publication or competition submission was performed. Kaggle/Linux compatibility, official hardware execution and hidden performance remain unverified. [S02, S19, S20]

> This report explains the research method, implemented architecture, positive and negative experiments, validation evidence, limitations and submission procedure. It accompanies the frozen package and does not change its code.

## Research objective and the simulation program

The project began from the hypothesis that an effective puzzle agent should behave more like a persistent scientist: accumulate experience, make explicit predictions, test alternatives, recognize contradictions and carry useful knowledge into later attempts. Human-like learning was treated as a source of engineering hypotheses. Success required measured transfer and retention, not an architectural label.

### What the early simulations tested

N1 compared a conventional gated recurrent unit, an adaptive-time-constant recurrent model and a spiking leaky integrate-and-fire model on next-position prediction. Training used 128 generated worlds with 96 steps each, three seeds per family, and four held-out conditions. The adaptive model was modestly better in some conditions; the GRU led on unfamiliar dynamics. The spiking model lagged under this protocol. Neither neural alternative passed its promotion gate, and no memory ablation passed its gate. [S03]

N2B tested longer schooling and a zero-prior control. Short driven learning solved 815/864 synthetic instances; extended driven learning solved 808/864; the zero-prior agent, which retained memory, planning and appraisal, solved 816/864. This result made it important to separate the value of external memory and planning from the value of a learned neural prior. These were synthetic mechanics tests, not ARC scores. [S04]

### Executable knowledge rather than a general education claim

N3 used a supplied interpreter with 357 rule templates, associative retrieval and recurrent revision of hypotheses. A second round of practice was selected using development failures. The neural hybrid included surrogate-gradient spikes and a liquid-inspired recurrent state; it was not a biological brain model. N3B changed the representation by adding object-role position statistics, but its retention gate failed despite improved aggregate school performance. [S05]

N4 expanded the executable vocabulary by 200 hypotheses across 18 lesson families, including rigid motion, cavity operations, propagation, periodic completion and conditional transforms. GRU and hybrid variants both solved 909/972 new-skill school instances and 22/400 public ARC-1 tasks. Both scored 0/55 queries on an independent ARC check. A broader curriculum helped taught mechanisms without establishing broad ARC generalization or a neural-cell advantage. [S06]

> The simulations were bounded grid and mechanics curricula. They did not implement a complete Earth simulator, university education, subjective emotion, whole-brain emulation or unrestricted invention of new concepts. These remain research ambitions rather than delivered capabilities.

## The submission system architecture

V138 is a fixed source package whose policy adapts its internal state while interacting with a game. A sequential driver starts a fresh policy process for each game and passes only the allowed observation fields: current frame, animation frames, state, available actions and completed-level count. The driver uses game identifiers for environment management and reporting; the policy interface does not receive them. [S08]

### Observable routing and preserved experts

An admission controller inspects the visible scene and available controls once, then selects an eligible specialist or the preserved parent policy. This is an engineered portfolio of controllers, not evidence that a concurrent LLM swarm solved the benchmark. It keeps successful earlier behavior available while adding narrowly qualified abilities. Scene-based specialization can still overfit public game families, even without receiving their identifiers. [S08]

| Specialist route | Main responsibility |
| --- | --- |
| Animated switch | Control effects and timing in animated navigation |
| Coupled marker | Joint marker alignment |
| Directional encounter | Position-dependent movement interactions |
| Beam split | Beam geometry and goal assignment |
| Key glyph | Visible symbols and control interpretation |
| Carry material | Material transport and transfer |
| Viewport peg | Cooperative motion and viewport reasoning |
| Measured waypoint | Observed movement range and intermediate positions |
| Binary temporal | Temporal fields, command programs and checkpoint persistence |
| Preserved parent | Previously qualified skills outside new admissions |

### Action and observation loop

Observe the visible scene; retrieve supported knowledge; propose a bounded action or program; execute through the environment; compare predicted and observed effects; retain the outcome; revise or stop when the model is refuted or its budget is exhausted. Different specialists implement different parts of this cycle. A failed probe is useful only when its result changes a later hypothesis or plan.

The delivered policy uses CPU execution. Optional Torch imports were blocked throughout V138 qualification, and this phase made no LLM calls. Earlier neural research remains part of the research record, but the V138 score is not evidence that a large language model or neuromorphic accelerator produced the measured gain. [S09, S12, S20]

## Retained knowledge and recursive learning

### Three distinct forms of memory

Within an episode, the learner retains observed control effects, earlier goal evidence, failed actions, field phases and outcomes of submitted plans. Across levels in a game, specialists can retrieve previously observed mechanisms, such as a control mapping or a patterned tile that preserves an intermediate position. Across research iterations, an external catalog preserves source pins, evidence, failed hypotheses and promotion decisions. These three forms of memory should not be conflated. [S09, S12]

The latest closed catalog contains 552 entries. They include research findings, negative results, audits, qualification records and delivery records; the number is not a count of 552 independently learned universal skills. The catalog and game-keyed failure index support research continuity. The submission carries executable policy source, not the full experiment archive or benchmark response traces. [S09, S18]

### How failures become usable evidence

A useful retained record connects a claim to the observation and action that support it. For example, a predicted stopping position is kept distinct from the actual post-action position. A checkpoint rule is linked to a prior visible motif and observed persistence. A refuted prediction remains a counterexample rather than being silently replaced with the intended result. Independent audit code tests whether these source bindings survive tampering. [S12, S13]

The V138 checkpoint extension copies the prior field model, known effects and failed-stop evidence before taking control. It records a semantic digest of the paused predecessor and asserts that the predecessor remains unchanged. It checks actual positions and level progress after submission, and stops on a refuted checkpoint or temporal prediction. It also bounds further attempts. This makes retention an executable property of the controller rather than a narrative promise. [S12]

### What recursive learning means here

At runtime, recursion means revisiting hypotheses after an observed error and using retained knowledge to construct a different plan. In the research workflow, it means selecting the next intervention from a diagnosed failure, testing it, and admitting it only after regression and whole-suite checks. Human direction and Codex-assisted engineering designed representations, curricula, code and experiments. The system did not autonomously invent the entire architecture or conduct unrestricted self-improvement.

> The checkpoint records 178,022 completed environment actions through its closed studies. This is a research-accounting total, not the cost of the final 7,585-action validation. Later partial V139 actions are not a completed evaluation and must not be added as an exact completed-run count. [S02, S09]

## Controlled evidence for retention and transfer

### Remembering joint goals after failure

A confirmation study used 16 reserved authored cases: eight joint-track goals and eight single-track regressions. Palettes, layouts, control directions and rotations varied. Forced failure erased visible goal information, making retention testable. The retained-memory treatment solved all 16 cases, compared with nine for the prior controller and zero for the forgetting control. All arms were executed and freshly replayed. [S10]

| Authored condition | Wins | Actions |
| --- | --- | --- |
| Prior controller | 9 / 16 | 456 |
| Retain goal and action evidence | 16 / 16 | 186 |
| Forget retained evidence | 0 / 16 | 62 |

The treatment gained seven cases with no paired losses. The forgetting control used fewer actions because it failed early, illustrating why lower action counts alone are not a success metric. A separate public diagnostic reached two levels in 128 actions with exact replay. The authored result supports a mechanism-specific transfer claim, not a public score or a human-equivalence claim. [S10]

### Reusing learned controls in reflection tasks

A separate sparse-reflection study varied palettes, shapes, layouts and control orientation across eight authored lessons. Retained control retrieval required 354 actions, compared with 378 when retrieval was ablated, saving 24 actions. The study included exact replay, semantic memory handoffs and rejection of seven forged evidence variants. It isolates a benefit from control retrieval under those conditions; it does not establish general transfer across arbitrary games. [S11]

### A counterfactual check on the final checkpoint learner

On the same adaptive public scene used for the V138 checkpoint improvement, the full memory supported a three-segment route. Removing checkpoint memory eliminated the route. Removing temporal memory reconstructed a program already observed to fail. A conservative alternative update order also found no route. These are offline counterfactual planning checks with zero new game actions, not fresh behavioral trials or a held-out generalization estimate. [S13]

> Evidence strength differs by study. Authored control comparisons, public development successes, offline memory ablations and complete public-suite evaluation answer different questions. The report keeps those denominators and scopes separate.

## Case study in learning from a failed approach

### From temporal prediction to checkpoint transfer

The final V138 improvement concerned a binary command and temporal-field task. Earlier attempts supplied evidence about control effects, changing obstruction fields and ordinary stopping positions that failed. The extension retrieved patterned-tile persistence from earlier levels and searched for a route through intermediate checkpoints instead of assuming that every intended stop would survive. [S12]

The agent formed a program from the visible control geometry, submitted it, compared the actual endpoint with the predicted endpoint, and retained the outcome. A checkpoint could be treated as useful only when linked to prior observations. The resulting public study won all seven levels in 190 actions; a fresh replay matched the actions and outcomes. The final full-suite V138 run then reproduced that result as part of all 25 games. [S01, S12]

| Qualification property | Recorded evidence |
| --- | --- |
| Public action sequence checked | 190 actions |
| Memory handoffs checked | 28 |
| Parent preservation checks | 191 |
| Forged evidence variants rejected | 9 |
| Checkpoint rules retained | 1 |
| Failed stops retained | 1 |
| Observed checkpoint outcomes | 3 |

The evidence audit rejected alterations to checkpoint outcome, motif, source, known effect, obstruction, phase source, predicted endpoint, failed stop and source binding. The complete suite score increased from 75.9925 in V137 to 76.9925 in V138, with one additional level and one additional complete game. [S01, S12, S17]

### Why the faster follow up was not submitted

A later experiment reused the failed execution more directly. It preserved the first 130 actions and complete responses, then won the same seven-level game in 160 actions. Fresh replay matched, saving 30 actions, or 15.79%, relative to the 190-action version. This was a valid single-game efficiency result with 23 memory handoffs per run. It was not a measured whole-suite score gain. [S14]

That experiment became the V139 proposal. Its preparation, qualification and build stages passed, but full-suite validation failed during disk exhaustion. No completed validation report exists for V139. The immediate handoff therefore retained V138. This decision preserved a verified result rather than treating a promising partial run as a finished candidate. [S02, S14]

## Goal interpretation and interaction coverage

### Goals require tested semantics

The research repeatedly encountered scenes where the geometry was visible but its meaning was uncertain. A target might require exact reproduction, coverage of positive marks, simultaneous satisfaction of several positions, or an intermediate state that enables a later action. More search under an incorrect goal interpretation can repeatedly produce the same failure. The retained catalog records alternative hypotheses and the observations that supported or refuted them. [S09]

Reflection work moved from matching complete goal templates toward testing whether visible target marks could be covered while extra reflected pixels remained. Additional repairs separated viewport borders before segmentation and retained evidence about partly occluded axes. Sparse-goal tests then checked reachability and object identity under changed layouts and controls. Several earlier click, visibility and identity-probe hypotheses completed no new levels and remained recorded as negative results. [S09, S11, S15]

### Transferring a deformation mechanism

Rectangle work retained an inferred deformation mechanism and its controls, then applied them to two rectangles with changed goal shapes and paint layouts. The public development record completed the eighth level in 748 total actions. Parsing clipped paint pads mattered to this transfer. This is evidence for that observed mechanism and tested layouts; it is not a proof that arbitrary shape transformations are covered. [S09, S15]

### Conditional motion and the edge of the viewport

A carrier-motion review reproduced 20 of 23 retained transition predictions exactly. The three exceptions involved boundary visibility: a predicted object could be absent, or an object could reappear unexpectedly. The next proposed experiment concerned persistence after disappearance and a lateral action while off-screen. Hidden positions were explicitly labeled hypotheses, not observations. [S16]

The carrier-prefix qualification preserved 549 previous actions, checked 80 memory handoffs and 549 parent states, and retained 329 motion records. That established a safe continuation point for a discriminating experiment. It did not establish a new public win. The queued public study was stopped when the user requested immediate packaging. [S02, S16]

> The common lesson is to improve the representation and test the uncertain interaction before broadening the planner. Goal semantics, timing and visibility errors are different failure classes; they require different interventions.

## Verified public progress

Each row below is a separate frozen candidate with a complete local public readiness record. The values are not assembled from the best game result of different versions. Repeated development on these public games makes the series adaptive; it is not an unbiased estimate on unseen games. [S17]

| Candidate | RHAE / 100 | Levels / 183 | Wins / 25 | Actions |
| --- | --- | --- | --- | --- |
| V114 | 54.3301 | 111 | 12 | 11,850 |
| V116 | 56.4730 | 116 | 12 | 10,920 |
| V117 | 57.3301 | 117 | 12 | 10,956 |
| V118 | 57.7587 | 119 | 12 | 10,121 |
| V121 | 67.8031 | 136 | 13 | 7,883 |
| V122 | 69.5128 | 141 | 13 | 6,484 |
| V123 | 70.3855 | 144 | 13 | 6,679 |
| V124 | 70.7535 | 145 | 13 | 6,972 |
| V125 | 70.8592 | 146 | 13 | 7,141 |
| V126 | 71.8592 | 147 | 14 | 7,100 |
| V128 | 72.9084 | 148 | 14 | 7,305 |
| V130 | 75.0471 | 150 | 15 | 7,246 |
| V132 | 75.0471 | 150 | 15 | 7,229 |
| V134 | 75.4834 | 151 | 15 | 7,385 |
| V137 | 75.9925 | 152 | 15 | 7,525 |
| V138 | 76.9925 | 153 | 16 | 7,585 |

### What improved

From V114 to V138, the local public score rose by 22.6624 points, completed levels rose from 111 to 153, and complete wins rose from 12 to 16. The final run used 4,265 fewer actions, although the policies and stopping behavior changed, so action reduction alone should not be treated as a controlled causal comparison. [S01, S17]

V121 contributed a large measured step over V118: 17 more completed levels and 10.0444 score points. Later gains were smaller and more targeted. V132 reduced actions relative to V130 without changing the reported score, levels or wins. V130 first exceeded 75 points in this series; V138 improved that result further, but the 100-point objective remained unmet. [S17]

> The local score and the public leaderboard are separate measurements. This report makes no claim that the candidate leads a competition or will win its hidden evaluation.

## The final 25 game evaluation

The V138 run covered every public game in the pinned local inventory. Sixteen games ended in a win; nine ended when the policy stopped. The run reported no runtime errors or external time-limit outcomes. The stopping games remain incomplete even when several of their levels were solved. [S01]

| Public game | Levels solved | Actions | Outcome |
| --- | --- | --- | --- |
| ar25-0c556536 | 8 | 302 | Win |
| bp35-0a0ad940 | 2 | 180 | Policy stopped |
| cd82-fb555c5d | 6 | 117 | Win |
| cn04-2fe56bfb | 6 | 383 | Win |
| dc22-fdcac232 | 4 | 341 | Policy stopped |
| ft09-0d8bbf25 | 6 | 125 | Win |
| g50t-5849a774 | 7 | 342 | Win |
| ka59-38d34dbb | 5 | 370 | Policy stopped |
| lf52-271a04aa | 7 | 520 | Policy stopped |
| lp85-305b61c3 | 8 | 215 | Win |
| ls20-9607627b | 6 | 712 | Policy stopped |
| m0r0-492f87ba | 6 | 338 | Win |
| r11l-495a7899 | 6 | 164 | Win |
| re86-8af5384d | 8 | 748 | Win |
| s5i5-18d95033 | 8 | 373 | Win |
| sb26-7fbdac44 | 8 | 124 | Win |
| sc25-635fd71a | 6 | 264 | Win |
| sk48-d8078629 | 4 | 142 | Policy stopped |
| sp80-589a99af | 6 | 207 | Win |
| su15-1944f8ab | 5 | 303 | Policy stopped |
| tn36-ef4dde99 | 7 | 190 | Win |
| tr87-cd924810 | 6 | 316 | Win |
| tu93-0768757b | 8 | 265 | Policy stopped |
| vc33-5430563c | 7 | 314 | Win |
| wa30-ee6fef47 | 3 | 230 | Policy stopped |

> Total: 153 levels completed, 16 game wins and 7,585 actions. All 183 levels remain in the aggregate denominator. Per-game counts are outcome summaries; no action sequence, response trace or answer file is included in this report.

## Validation and experimental discipline

### A promotion sequence with explicit gates

The final sprint required legal observations, retained failure evidence, exact fresh replay for an actual gain, preservation of earlier state and full uncached validation over all 25 games before promotion. The policy was frozen for a validation run. Source and runtime fingerprints were checked so a measured result could be tied to the delivered bytes. [S01, S18, S22]

A narrow experiment first tested a specific intervention. Qualification then checked prior action behavior, memory handoffs and evidence certificates, including intentionally forged variants. Successful public changes were replayed in fresh environments. The composed candidate was finally run through the full suite, with action, response and outcome comparisons. These checks support reproducibility and retention; they do not remove prior public-data exposure. [S01, S12]

### What was verified for V138

| Check | Result |
| --- | --- |
| All 25 games evaluated uncached | Passed |
| Action response and outcome comparisons | All exact |
| Source and runtime unchanged | Passed |
| Expected package members and source syntax | Passed |
| Benchmark response files in policy package | 0 |
| Fresh final initialization check | Passed with 0 game actions |
| Kaggle Linux and official hardware run | Not performed |

The local validation took about 1,335.61 seconds, or 22.3 minutes, in the recorded Windows environment. Its owned-process receipt recorded completed cleanup. The final delivery check independently verified source hashes and initialized the guarded policy; it did not rerun games or create a new score. The package audit recorded 558 source-package members, including 557 under its policy-file count, and zero benchmark response files. [S01, S18, S19, S21]

### Interpretation safeguards

A fresh replay is a new execution, not a hidden or previously untouched test set. Exact reproduction says the recorded behavior can be repeated under pinned conditions. It does not establish robustness to all seeds, operating systems, altered game rules or unfamiliar visual structures. Likewise, an offline ablation reveals what a planner uses in a retained scene; it is not equivalent to a fresh randomized behavioral experiment.

> Earlier transfer work discovered overlap between confirmation and development pools and withdrew the corresponding independence claim. The corrected independent check did not reproduce the apparent gain. Keeping that correction visible is part of the research record. [S07]

## Reproducibility and the submission handoff

### The frozen artifact

The submission notebook embeds the policy source archive and verifies its SHA-256 before extraction. The separate policy ZIP is an inspectable copy of those same bytes. The handoff also contains requirements, optional private-notebook metadata, readiness and validation summaries, runtime pins, checksums and a local verifier. It excludes benchmark traces, response caches, game implementations, private credentials and answer files. [S18, S20]

| Locally tested component | Version or condition |
| --- | --- |
| Coordinator Python | 3.12.14 |
| Policy Python | 3.10.0 |
| NumPy | 2.2.6 |
| SciPy | 1.15.3 |
| ARC SDK distribution | arc-agi 0.9.9 |
| Game engine distribution | arcengine 0.9.3 |
| Execution | Windows CPU; optional Torch unused |

These are local evidence pins, not proof that the Kaggle runtime has identical dependencies. The notebook installs official wheels offline and checks NumPy/SciPy imports and policy initialization. It sets CPU execution and single-thread numerical-library limits in the policy process. Configured budgets are 1,024 actions per game, 600 wall seconds per game, 28,800 internal run seconds, and a guarded policy budget of 600 CPU seconds and 2 GiB. [S08, S20]

### User submission procedure

Import submission.ipynb as a private competition notebook, attach the competition data, select CPU and keep Internet off. Save and run all cells; inspect initialization logs. The ordinary commit run creates an explicitly unscored submission.parquet schema fixture. During competition rerun, the notebook waits for the official gateway and runs the agent; the gateway produces the actual evaluation result. The fixture is not a benchmark score. [S20]

### Integrity identifiers

> Notebook SHA256  e29cb39ca485a5d0efcaf6f63b3122eaeabfbe80f0079aabb383e1def78087a3

> Policy archive SHA256  b992030ca9dad1998af5f7612f196fa68b58b08c3c40a87411d1c1cbc81623cb

> Submission handoff ZIP SHA256  47d18d614f405882a0660d1cf4e6aa78d943439384e2b91990a6a6d235ec3ae1

> The notebook deployment contract was checked against official starter commit eeb1535404f321d280a8f9194bbc1d7aca5f05fc. Hosted initialization and submission acceptance remain user-side checks. This report does not claim a new verification of current platform rules. [S20]

## Limitations and conclusions

### What the results support

The project demonstrated that selected forms of retained evidence can improve specific planning and control tasks. Authored controls showed benefits from retaining goals and learned controls. Public case studies showed an agent using prior effects, temporal observations and checkpoint persistence to complete later tasks. Complete frozen-candidate validation established the final local score and preserved prior behavior. The supported conclusion is practical and bounded: carefully represented experience can make a puzzle agent more effective. [S01, S10-S13]

### What remains unresolved

Public games were repeatedly used to diagnose failures and guide interventions. The controller portfolio contains substantial engineered visual and procedural knowledge. Hidden-game generalization is therefore unknown. The final local run leaves 30 levels and nine full games unfinished; the 100-point objective was not reached. A fixed-seed replay cannot establish robustness across different seeds, renderings, action mappings or timing behavior. [S01, S08]

The experiments do not establish human-level reasoning, brain equivalence, emotion, a general neuromorphic advantage or the necessity of a particular neuron model. Earlier school gains often exceeded public transfer, and some apparent improvements failed retention or independence checks. The strongest final result was qualified without optional Torch imports and without LLM calls. These facts should remain explicit in any competition write-up or public description. [S03-S07, S12]

### Recommended research after the submission

First, establish operational reliability on the official runtime and separately measure hidden or genuinely reserved tasks. Second, preregister transfer tests that change visual appearance, action mapping, object count and interaction rules while holding budgets fixed. Third, test missing roles, off-screen persistence and conditional motion using competing predictions with an observable discriminating action. Fourth, compare memory and planning ablations at matched compute, and measure both new gains and regressions.

Any renewed neuromorphic study should compare against a strong conventional recurrent control using matched data, capacity where feasible, compute and action budgets. The outcome should be a prospective task or transfer gain, not simply a different internal state representation. Broader simulation knowledge is valuable only when its effect survives that evaluation.

### Closeout

The user selected immediate delivery. V138, older verified candidates and retained research knowledge were preserved; V139 was not promoted; scheduled research was stopped. The report and its evidence index add documentation without modifying the frozen submission. The next operational decision is the user-side Kaggle initialization and submission workflow. [S02]

## Evidence register

Source identifiers refer to local research artifacts. The accompanying evidence index records every referenced path, SHA-256 and byte count. It contains provenance metadata only; raw experiments and benchmark traces remain outside the delivery.

### S01 V138 final validation and measured run

All 25 games, score, levels, wins, actions, exact comparisons and measured runtime.

> outputs/arc3-kaggle-uncached-v138-r1-v1/VALIDATION.json

> outputs/arc3-kaggle-uncached-v138-r1-v1/run/RESULT.json

### S02 Immediate submission handoff

Selected candidate, excluded V139, final artifact hashes, research stop and automation deletion.

> outputs/ARC3-Immediate-Submission-Handoff-v138-2026-11-02.json

### S03 Neural dynamics pilot

N1 controls, prediction results and failed neural promotion gates.

> outputs/neuro-world-lab/N1-REPORT.txt

### S04 Schooling and zero prior controls

Synthetic schooling outcomes and distinction between memory and neural priors.

> outputs/brain-school-lab/N2B-REPORT.txt

### S05 Relational curriculum and recursive hypotheses

N3 and N3B training design, supplied program vocabulary and limits.

> outputs/learning-repository-n3b/RESEARCH-REPORT.txt

### S06 Broader executable world knowledge

N4 curriculum, school performance, conventional control, public transfer and ablations.

> outputs/world-knowledge-n4/RESEARCH-REPORT.txt

### S07 Early transfer and overlap correction

Early ARC results, neural control comparison and withdrawn independence claim.

> outputs/arc-transfer-lab/RESEARCH-REPORT.txt

### S08 Frozen policy entry and observable routing

Process interface, observable admission, preserved fallback and runtime budgets.

> outputs/reliable-arc3-hybrid-v138/student.py

> outputs/reliable-arc3-hybrid-v138/reliable/retained_coverage_admission_v18.py

> outputs/arc3-submit-now-v138-final-check-v1/source/client.py

## Evidence register continued

Source identifiers refer to local research artifacts. The accompanying evidence index records every referenced path, SHA-256 and byte count. It contains provenance metadata only; raw experiments and benchmark traces remain outside the delivery.

### S09 Retained research catalog and checkpoint

552 research entries, retained findings and completed action accounting.

> outputs/ARC3-Retained-Skill-Catalog-2026-11-02-v85.json

> outputs/ARC3-Resumed-Research-Checkpoint-v85-2026-11-02.json

> outputs/ARC3-Failure-Retrieval-Index-v85.json

### S10 Joint goal memory confirmation

Authored retained versus prior versus forgetting controls, and separate public diagnostic.

> outputs/intersecting-track-confirmation-v1/SUMMARY.json

> outputs/intersecting-public-transfer-v1/RESULT.json

### S11 Sparse reflection transfer qualification

Eight authored lessons, retained control retrieval, exact replay and tamper rejection.

> outputs/sparse-reflection-qualification-v3/RESULT.json

### S12 Binary checkpoint learner and successful public replay

V138 checkpoint transfer, public win, semantic handoffs and evidence audits.

> work/binary_checkpoint_temporal_inquiry_v1.py

> outputs/binary-checkpoint-public-v2/RESULT.json

> outputs/retained-coverage-qualification-v138/RESULT.json

### S13 Checkpoint and temporal memory ablation

Offline counterfactual removal of retained rules and temporal evidence.

> outputs/binary-checkpoint-memory-ablation-v1/RESULT.json

### S14 Failure reuse efficiency experiment

160-action replay, frozen-prefix preservation and failed full-suite V139 stage.

> outputs/binary-failure-checkpoint-prefix-v1/RESULT.json

> outputs/binary-failure-checkpoint-public-v1/RESULT.json

> outputs/binary-v139-qualification-pipeline/RESULT.json

### S15 Rectangle and reflection development

Public development results for deformation and reflection goal interpretation.

> outputs/shape-site-public-v22/RESULT.json

> outputs/reflection-assignment-public-v16/RESULT.json

## Evidence register continued

Source identifiers refer to local research artifacts. The accompanying evidence index records every referenced path, SHA-256 and byte count. It contains provenance metadata only; raw experiments and benchmark traces remain outside the delivery.

### S16 Carrier boundary diagnosis

20 of 23 motion predictions, boundary hypotheses and preserved 549-action prefix.

> outputs/retained-carrier-projection-review-v1/RESULT.json

> outputs/carrier-permanence-prefix-v1/RESULT.json

### S17 Verified candidate progression

Each table row is a separate frozen candidate readiness record, not pooled best-game scores.

> 16 pinned source files are enumerated in the evidence index.

### S18 Source package audit

Source equality, expected archive members, syntax and response-file exclusion.

> outputs/arc3-kaggle-uncached-v138-r1-v1/PACKAGING-AUDIT.json

> outputs/arc3-kaggle-uncached-v138-r1-v1/SOURCE-PINS.json

### S19 Final local initialization check

Fresh source verification and guarded initialization with zero game actions.

> outputs/arc3-submit-now-v138-final-check-v1/VERIFICATION.json

### S20 Runtime and submission instructions

Tested dependencies, notebook deployment contract, commit fixture and competition rerun.

> 4 pinned source files are enumerated in the evidence index.

### S21 Owned validation process receipt

Validation ownership, runtime and completed cleanup.

> outputs/arc3-kaggle-uncached-v138-r1-v1/OWNER.json

### S22 Twenty hour research and packaging plan

Promotion requirements, failure-driven priorities and local-only restrictions.

> outputs/ARC3-Twenty-Hour-Research-Plan-2026-11-01-v73.json
