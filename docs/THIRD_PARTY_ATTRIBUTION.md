# Third-party rule references

The Human Voice implementation is native Python and does not vendor third-party
runtime code. Its deterministic rule families and test ideas were reviewed
against these public projects:

- [YottaMeta/yotta-humanize](https://github.com/YottaMeta/yotta-humanize): MIT
  licensed detector/rewrite flow, rule reports and CI-friendly JSON. No source
  files are copied into this repository.
- [jiji262/humanizer-chinese](https://github.com/jiji262/humanizer-chinese):
  Chinese AI-writing patterns, rhythm and voice-calibration guidance. The
  repository uses independently written, narrower rules for X editorial review.
- [lynote-ai/humanize-text-skill](https://github.com/lynote-ai/humanize-text-skill):
  subtraction/addition framing and protected-span review. The repository keeps
  fact locking and publication gates as local contracts.

Upstream licenses and terms remain with their respective projects. This note is
an attribution and design reference, not a claim that upstream behavior proves
the quality of this account's writing.
