# Reminder: Include the Strategy C Experiment Log Skill

Whenever you request an exploratory experiment, validation sweep, or any investigative work around Strategy C, please mention the Strategy C Experiment Log skill in your prompt. This ensures the downstream agent realizes it must update a log under `development_strategy/strategy_C/obs/` with the prescribed template.

For the repo-local logging rules, see:

- `development_strategy/strategy_D/log_strategy_d_approach_baseline.md` for the
  reclassified non-`autoreject` baseline path

For example:
- “Using Strategy C, explore a frontal consensus signal and log the findings with the Strategy C Experiment Log skill.”
- “Can you run an exploratory parameter sweep for Strategy C? Include the Strategy C Experiment Log skill so we keep the log updated.”

Failing to mention the skill may cause the log update to be overlooked, so include the name every time you expect a structured log entry.
