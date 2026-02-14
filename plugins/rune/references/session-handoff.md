# Session Handoff Template

Write to `tmp/scratch/session-state.md` before compaction or at session end.

## Session State

```markdown
- Workflow: {review|plan|work|mend|arc}
- Phase: {current phase number and name}
- Team: {team-name}
- Checkpoint: {path to checkpoint.json if arc}
- Active teammates: {list of teammate names still running}
- Completed artifacts: {list of output files already written}
- Files to read next: {specific files needed to resume}
- Files NOT to re-read: {completed research/review outputs}
- Open questions: {any unresolved decisions}
- Next action: {exact next step}
```
