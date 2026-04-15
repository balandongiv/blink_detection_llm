# Development Strategy Documentation

This directory contains strategic planning and decision logs for the pyblinker epoch detection project.

## Files

### log_strategy_c/
Named Strategy C history files live under `development_strategy/log_strategy_c/`.
Use a new file per major approach, for example:

- `development_strategy/log_strategy_c/log_strategy_c_approach1.md`
- `development_strategy/log_strategy_c/log_strategy_c_approach2.md`

These files are the durable record of strategies proposed, implemented, tested, and their effects on the project. This is the primary artifact for tracking:

- **What** strategies have been tried
- **Why** each strategy was chosen
- **What** code changes implemented each strategy  
- **How** each strategy affected performance/results
- **What** was learned from each attempt

**When to update**: Create a new named file whenever a significant Strategy C approach is proposed or evaluated. Update that file as implementation proceeds.

### Other Strategy Documents

- **strategy_A_development_plan.md**: Original development approach for Strategy A
- **strategy_C_development_plan.md**: Development approach for Strategy C (epoch-aware detection)
- **test_strategy.md**: Testing and validation approach
- **tap_autoreject_approach.md**: Approach documentation for tap/autoreject functionality

## Using the Strategy Log

### Creating a New Entry

When you have a new idea or strategy:

1. Open the current named Strategy C log under `log_strategy_c/`
2. Add a new `## Strategy: [Name]` section
3. Fill in:
   - **Date**: Today's date
   - **Proposal**: What is the core idea?
   - **Rationale**: Why should we try this?
   - **Status**: Proposed
4. Save and share the link

### Implementing a Strategy

As you make code changes:

1. Update the **Implementation** section with file paths and lines changed
2. Add commit hashes as you commit work
3. Update **Status** to "In Progress"

### Measuring Results

After implementation:

1. Run tests/benchmarks
2. Update **Performance & Metrics** with before/after numbers
3. Record the data source (which test file, which output)
4. Document **Issues Encountered** if any arose

### Concluding a Strategy

When work is complete:

1. Set **Status** to "Completed" or "Abandoned"
2. Write the **Outcome** (did it work? why?)
3. Extract **Learnings** (what did we learn? what would we do differently?)
4. Save final entry

## Example Entry

```markdown
## Strategy: Epoch-Aware Blink Detection Pipeline

**Date**: 2026-04-02
**Proposal**: Integrate blink detection with epoch handling, allowing bad epochs to be excluded
**Rationale**: Current detection operates on raw data without epoch awareness. With epochs, we can:
- Automatically exclude marked bad epochs
- Preserve epoch metadata in results
- Cleaner integration with epoch-based analysis pipelines

**Status**: Completed

### Implementation
**Files Changed**:
- `pyblinker/epoch_detection_strategy_c/pipeline.py` (lines 1-250): New epoch-aware pipeline

**Commits**:
- `9a5ffe9`: feat: Add epoch-aware blink detection pipeline with bad epoch exclusion

### Performance & Metrics
**Before**: No epoch-aware pipeline
**After**: 950 valid epochs processed in 38 seconds, bad epochs properly excluded

**Data Source**: sample_data/dev_epo.fif

### Issues Encountered
- Path references to old data location
  - *Resolution*: Updated paths in commit 1a6c166
  - *Status*: Resolved

### Outcome
Success. Pipeline works as intended, ready for production.

### Learnings
- Working with epoch structures requires careful boundary handling
- Defensive coding for missing annotations prevents data loss
- Epoch exclusion benefits from regex-based pattern matching
```

## Quick Reference

### Command to View the Current Strategy C Log
```bash
cat development_strategy/log_strategy_c/log_strategy_c_approach1.md
```

### Key Metrics to Track
- **Performance**: Latency, throughput, memory usage
- **Quality**: Accuracy, precision, recall, F1 score
- **Reliability**: Error rates, edge cases, failure modes
- **Maintainability**: Code complexity, test coverage, documentation

### Common Mistakes to Avoid

❌ Don't create entries after implementation  
✅ Create entries before, update as work progresses

❌ Don't claim success without metrics  
✅ Always cite data sources and specific numbers

❌ Don't hide failures or trade-offs  
✅ Document honestly; failures are learning opportunities

❌ Don't delete old entries  
✅ Keep all entries; they document solution evolution

## Integration with Code

Every strategy entry should link to the code that implements it:

- Specific file paths: `path/to/file.py (lines X-Y)`
- Commit hashes: Track changes as `abc1234: commit message`
- Test files: Reference validation that proves impact

This creates a bidirectional connection: 
- Strategy Log → Code
- Code (via git blame) → Strategy Log

## Using Strategy Log for Future Decisions

When proposing a new strategy, check the log:
- Have we tried something similar? What happened?
- What trade-offs did other approaches involve?
- Are there patterns in what works or doesn't work?
- Can we avoid repeating failed approaches?

## Questions?

Refer to the full skill documentation in `agent-skillbook/skills/strategy-impact-log/INSTRUCTIONS.md`
