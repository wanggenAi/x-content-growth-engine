# Human Style pipeline

Every new candidate is reviewed through this local, deterministic sequence:

`material → fact lock → human tension → reader model → raw draft → run_human_style_pipeline() → AI flavor → rewrite when needed → fact preservation → X Native Style → Comment Impulse → Editorial Gate → READY_FOR_MANUAL_PUBLISH`

The implementation lives in:

- `growth_engine/ai_flavor_gate.py` detects Chinese templates, abstract-noun density, over-explanation, rhythm uniformity, rhetorical-question abuse and forced humanization. `analyze_ai_flavor()` returns a JSON-safe report. A high score is a blocker signal, not an authorship detector and not a goal of zero.
- `growth_engine/candidate_pipeline.py` is the production entry for new candidates. `prepare_candidate()` refuses synthetic blind fixtures, runs Human Style before admission, writes the rewritten text and the generated contract, then invokes the Editorial Gate.
- `growth_engine/human_voice.py` implements `run_human_style_pipeline()` and the hash-bound `HUMAN_STYLE_V2` contract. It protects URLs and quoted spans, removes only known editorial residue, records the raw first reaction and can leave an already-natural draft unchanged. The historical `run_human_voice_pipeline` symbol remains an alias.
- `growth_engine/fact_preservation.py` compares locked numbers, dates, names/entities, URLs and direct quotes, and flags new causal claims. Any drift is `HOLD_FACT_DRIFT`.
- `growth_engine/x_native_style.py` scores scene concreteness, first-screen stopping power, rhythm, abstraction, explanation load and conclusion overreach. `review_comment_impulse()` is required for `REPLY`: a moral-consensus question with an obvious answer fails even when it is grammatically polished.
- `growth_engine/editorial_gate.py` requires the compact contract for `READY_FOR_MANUAL_PUBLISH`. Historical `PUBLISHED_PENDING_FEEDBACK`, `OBSERVATION_CLOSED` and `LEARNING_REVIEWED` records remain readable without it.

The default profile is [data/voice_profiles/gen_default.json](../data/voice_profiles/gen_default.json). It describes structural preferences learned from multi-author sample review; it does not copy an individual author. The profile favors concrete scenes, mixed sentence lengths, low abstraction and open endings. It does not add typos, profanity, random emojis or invented first-person experience.

The implementation was informed by the rule/report shape in [YottaMeta/yotta-humanize](https://github.com/YottaMeta/yotta-humanize), Chinese pattern and calibration guidance in [jiji262/humanizer-chinese](https://github.com/jiji262/humanizer-chinese), and the subtraction-plus-addition framing in [lynote-ai/humanize-text-skill](https://github.com/lynote-ai/humanize-text-skill). No external model, paid API or third-party runtime is required in pytest or CI; attribution is recorded in [THIRD_PARTY_ATTRIBUTION.md](THIRD_PARTY_ATTRIBUTION.md).

## Contract

The request to `run_human_style_pipeline()` includes `draft_text`, `locked_facts`, `target_platform`, `voice_profile`, `primary_action`, `source_context` and `preserve_quotes`. The result includes `rewritten_text`, auditable `operations`, `voice_features`, warnings, detailed gate reports and a generated contract:

```json
{
  "version": "HUMAN_STYLE_V2",
  "input_text_hash": "...",
  "output_text_hash": "...",
  "locked_facts_hash": "...",
  "ai_flavor_score_before": 42,
  "ai_flavor_score_after": 18,
  "x_native_style": "PASS",
  "fact_preservation": "PASS",
  "comment_impulse": "PASS",
  "rewrite_applied": true,
  "evaluated_at": "...",
  "engine_version": "human-style-v2-deterministic",
  "generated_by": "growth_engine.candidate_pipeline.prepare_candidate"
}
```

The Editorial Gate recomputes all three hashes and rejects a hand-filled or stale contract. Historical `HUMAN_VOICE_V1` records remain readable in published states, but new READY candidates can only be produced by `prepare_candidate()`.

`comment_impulse` is `NOT_APPLICABLE` for actions such as `SHARE`. A passing Human Voice contract does not publish a post by itself: human review and the existing manual X publication checks still apply.

## Replay

[data/human_voice_replay_2026-10-16.json](../data/human_voice_replay_2026-10-16.json) records a simulation over C387, C388 and C389 without changing their published files. C387's original author verdict is removed in the simulated rewrite. C388 remains held for its fact-to-fairness mini-essay and obvious-answer reply. C389 is retained as a concrete, quoted SHARE draft.
