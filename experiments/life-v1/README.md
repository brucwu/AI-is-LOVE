# Life Director v1 experiment

Protocol: seven virtual days, one representative slice every six hours (28 slices), no player intervention. Start at 06:00 America/Los_Angeles on the experiment date. One persistent in-memory CharacterRuntime is used throughout a run; the endpoint starts a fresh runtime for each experiment. No database or autonomous background life loop is implemented yet.

`run-1.json` and `run-2.json` are the preserved responses from the deployed `/experiments/life` POST. Each `commit_sha` identifies the implementation used, independently of the later documentation commit. Categories and participants are model-reported; semantic diversity and continuity require reading the actual experiences, not only counts.

The v0 comparison uses the handoff's known findings (28 slices, 11 memories, apartment/domestic repetition). The full v0 raw trace was not supplied in the repository, so this is not a statistical paired comparison.

See `ANALYSIS.md` for deployment evidence, both runs, the engineering iteration, comparison and remaining weaknesses. `run-*-metrics.json` contains counts calculated from each preserved trace.
