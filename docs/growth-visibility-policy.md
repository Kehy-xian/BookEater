# BookEater growth visibility policy

## Product rule

Growth is **hidden genetics, visible phenotype**.

The classifier may internally use response/world labels, lexical evidence, semantic scores, confidence, thresholds and cumulative nutrition. Ordinary players must not see those mechanics as a per-record explanation or a stat sheet.

The game should feel as if the monster digests a long history of reading rather than grades each sentence.

## Player may see

- current creature form and stage
- visible body mutations or accessories
- a broad, narrative tendency hint, especially after later evolution
- generic feeding reactions such as “기록 한 조각을 꿀꺽 삼켰다.”
- a coarse optional quality signal such as “이 성장 반응이 좀 이상해요”

## Player must not see

- internal labels (`사유`, `탐구`, `감정`, `감각`, `상상`, `모험`, `자연`, `사회`, `어둠`)
- keyword-hit explanations
- per-record percentages, scores, confidence or contribution amounts
- “이 단어 때문에 이 형태가 됨” style causal explanations
- exact evolution recipes or target-keyword guides
- a radar/stat panel that lets a player reverse-engineer the classifier

Developer/research diagnostics may expose these values only in a clearly separate debug tool, never through the ordinary play surface.

## Why this is intentional

1. Reading records are ambiguous. A single sentence can plausibly carry several meanings.
2. Long-term accumulated tendency is the product signal; exact per-entry classification is not the player contract.
3. Small isolated classifier errors should wash out across many records rather than become visible disputes.
4. Hidden mechanics make it harder to game evolution by typing target words and make discovery more interesting.

Opacity is not permission to ignore quality. Systematic bias can still distort the final phenotype, recommendations and replay value. Evaluation therefore prioritizes long-run stability, abstention on irrelevant records, severe false-positive control and plausible aggregate evolution, while continuing to improve per-record precision/recall in diagnostics.

## UX cadence

- Stage 0–1: almost no explanation. Show growth and generic reactions.
- Stage 2: one vague sentence about a developing habit or interest.
- Stage 3/final: one broad body-tendency description and, when visually obvious, up to two broad world-flavor hints.
- Never reveal a numerical recipe even after final evolution.

## Feedback policy

Ordinary players may optionally report that a growth reaction felt strange. They do not select the correct hidden label. An omitted correction is **not** interpreted as an explicit empty-label correction.

Explicit label corrections are reserved for controlled developer/research tooling.

## Quality gate implication

A release should be blocked by patterns such as repeated false world modifiers, frequent base-type oscillation, poor NULL abstention, or aggregate evolution that conflicts with a long coherent reading history. One isolated arguable label miss is a diagnostic issue, not necessarily a product-visible failure.
