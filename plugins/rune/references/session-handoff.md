# Session Handoff Template

Write to `tmp/scratch/session-state.md` before compaction or at session end.

## Session State

```markdown
- Workflow: {review|audit|plan|forge|work|mend|arc}
- Phase: {current phase number and name}
- Team: {team-name}
- Checkpoint: {path to checkpoint.json if arc}
- Active teammates: {list of teammate names still running}
- Completed artifacts: {list of output files already written}
- Files to read next: {specific files needed to resume}
- Files NOT to re-read: {completed research/review outputs}
- Open questions: {any unresolved decisions}
- Gap analysis: {summary of missing/partial items from Phase 5.5, if arc}
- Next action: {exact next step}

## Arc-specific fields (optional, for /rune:arc workflows):
- Convergence round: {current mend retry count, e.g., 0/2}
- Flags: {--approve, --no-forge, etc.}
- Phase sequence position: {index in PHASE_ORDER array, e.g., 5/10}
```
