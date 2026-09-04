# BookEater Product Roadmap v1

> Historical planning document. For the repository's current implemented/missing status, use
> `IMPLEMENTATION_STATUS_2026-09-02.md`; many items originally listed below as "next" are now built.

## Product principle

BookEater is a local-first desktop pet that grows from reading records. Internal NLP traits, keywords, confidence scores, thresholds and exact evolution recipes remain hidden from players. The player sees only phenotype, mood, dialogue, memories and broad tendency hints.

## Implemented now

### Local reading and growth core
- Local SQLite persistence under the user's app-data directory.
- Save-first reading records with pending/retry recovery when the local model is unavailable.
- Bundled multilingual E5 ONNX semantic analysis and conservative hidden growth projection.
- Layered evolution: reading-response tendencies affect body lineage; world/theme tendencies affect modifiers.
- Bookkeeping-only notes do not advance growth.
- Internal classifier details are excluded from player-facing payloads.
- Regression/blind test suites and Windows CI packaging smoke.
- Growth-art topology now explicitly models the approved starter and sibling second-growth routes.

### Approved first evolution topology
The currently approved visual tree is structurally:

`기본 글씨알 (tier 0) -> Route A OR Route B (both tier 1)`

- Route A and Route B are the same growth level.
- Route A is not a prerequisite for Route B and Route B is not an upgrade of Route A.
- Direct A -> B and B -> A transitions are invalid.
- The exact hidden reading-pattern rule that chooses A versus B remains intentionally undecided until the route meanings are approved; do not invent or expose a keyword recipe.
- Later tiers may branch again, but they must be modeled as children of the chosen tier-1 route rather than pretending A and B are sequential stages.

### Book journal
- Books are registered once and can have many chronological reading notes.
- Title is required; author is optional for manual entry.
- Optional progress text (page/chapter/etc.) is stored separately from the note text so it does not contaminate NLP.
- Recently read books are shown first.
- Same book can receive repeated notes over days/weeks.
- Book timeline view is available locally.

### Monster milestones
- Store a stable `met_at` date separately from the encyclopedia.
- For legacy data, use the earliest existing reading-record date as the best available historical meeting-date approximation rather than rewriting history to the update date.
- `first_fed_at` is derived from the earliest successfully consumed reading record.
- These dates are player-facing life-history metadata, not hidden NLP traits.

### Desktop pet shell
- Transparent small window on Windows.
- Always on top.
- Drag to move.
- Double click opens reading-record entry.
- The right-click menu exposes feeding, memories, recommendations, bookshelf, encyclopedia,
  current-monster care/profile, tray rest, data/settings and guarded exit actions.
- The desktop shell renders validated replaceable sprite states, with a vector fallback when a
  complete sprite set is unavailable.
- Production art contract exists for idle/eat/walk/read/sleep/talk/spit_memory sprite states.
- The roaming engine is integrated with boundary-safe horizontal/vertical/diagonal motion,
  walking/running, pauses, sitting, dozing, edge bumps and drag/drop interruption.

### Windows build
- PyInstaller one-folder Windows build.
- Bundled ONNX model/tokenizer verified in CI.
- Packaged runtime smoke verifies model loading and local SQLite creation.

## Next implementation: desktop-pet experience

### 1. Production character art
- The base `글씨알` is the approved rounded paper-egg concept.
- The two other approved concepts are sibling second-growth forms: Route A and Route B.
- Produce starter IDLE/EAT/WALK first; use those desktop-scale tests to lock sprite readability before multiplying frames across every evolution form.
- Then add READ/SLEEP/TALK/SPIT_MEMORY.
- Left/right movement may mirror one side-facing sprite; front/back views are not mandatory unless an interaction needs them.
- Evolution forms reuse the same state contract so art can be added without changing NLP/database logic.

### 2. Desktop roaming behavior
Target ambient loop:
- idle/blink/breathe
- choose a nearby visible target
- waddle/walk toward it without leaving the Windows work area
- pause
- occasionally read, doze or talk
- resume roaming

Interactions such as feeding, memory-spitting, first-run drop animation, dragging, menus and mini-games interrupt autonomous roaming safely. User drag must never fight the movement controller.

### 3. Player-facing pet menu
Target menu:
- 기록 먹이기
- 내 서재
- 기억 꺼내기
- 돌보기
- 몬스터 도감
- 설정
- 종료

### 4. Personality and dialogue engine
- Pet personality is derived from long-term hidden growth history, not exposed labels.
- Dialogue tone changes gradually with the formed personality.
- Dialogue sources:
  1. generic personality lines,
  2. resurfaced reading memories,
  3. commentary on a resurfaced memory,
  4. book recommendations based on accumulated reading history,
  5. context lines for care, sleep, reading and idle states.
- Avoid claiming a memory or recommendation was caused by a specific hidden keyword.

### 5. Memory resurfacing
- Retrieve past local notes using local semantic search.
- `기억 꺼내기` can surface a past note, book title, date/progress context and a short pet reaction.
- Future quiz mode can build deterministic questions from the user's own notes.

### 6. Recommendations
- Recommend only real catalog/API candidates; never invent book titles.
- Two hidden ranking intents remain available internally: taste-deepening and breadth-expanding.
- Player-facing explanation is natural-language and broad, not a trait-score report.

### 7. Auto-start option
- Windows per-user startup toggle, default OFF.
- Store setting locally.
- Prefer HKCU per-user startup or an equivalent no-admin mechanism.
- Setting can be turned on/off at any time.

### 8. First-run drop animation
- On the first-ever successful launch, the pet drops from above the visible work area and lands with a small bounce (`콩`).
- Persist a local `intro_seen` flag so it does not replay every boot.
- Provide an optional `인트로 다시 보기` setting later.

### 9. Care loop and mini-games
Care is deliberately separated from reading genetics.
- 밥주기: affects satiety/mood, not reading evolution.
- 놀아주기: affects mood/bond.
- 씻기기: affects cleanliness/mood.
- Simple mini-games may improve bond and trigger dialogue/animations.
- No death, irreversible punishment or forced daily streaks.
- Soft needs may decay slowly, but neglect must not erase reading progress.

### 10. Monster encyclopedia / collection
- Encyclopedia records every form the user has actually encountered.
- Unknown forms remain silhouettes/locked entries.
- Each unlocked entry should stay deliberately simple: form image/name plus one broad personality-flavored hint sentence, not the hidden evolution formula.
- `만난 날` and `처음 기록을 먹인 날` belong to the current-monster profile/life-history view, not the encyclopedia entry itself.
- To make multiple evolution lines genuinely collectible, a later loop is needed: a fully grown monster can be archived to the user's `서고`, then the user may raise a new `글씨알` while keeping previous monsters in the collection.
- Never overwrite or delete the history of a retired/archived monster.

## Art production scope

Do not draw every evolution from every angle up front.

For the first production milestone:
- Base `글씨알`: canonical design sheet + IDLE 4 + EAT 6 + WALK 4.
- After desktop-size readability is approved: READ 3 + SLEEP 3 + TALK 2 + SPIT_MEMORY 4.
- Left/right can be mirrored unless asymmetrical visual modifiers require dedicated frames.
- Back view is optional, not a requirement for every form.

For evolution lines:
- Route A and Route B are sibling tier-1 forms and each gets its own canonical silhouette.
- Each form only needs the states actually used by the game; reuse motion templates where practical.
- World/theme modifiers should be modular visual motifs where possible, rather than redrawing every 4×5 combination as a completely independent full sprite set.

## Data safety / update rules
- User books, notes, corrections, monster history, milestone dates, settings, encyclopedia unlocks and archived monsters are user data and must never be overwritten by app updates.
- Model/app updates can add new analysis versions but may not silently rewrite past user corrections or past monster history.
- Care state may evolve over time, but reading/evolution history is permanent unless the user explicitly resets it.

## Near-term order
1. Integrate the approved starter art as production-scale IDLE/EAT/WALK sprites.
2. Connect the roaming state engine to the transparent Windows pet and stress-test drag/menu/feed interruptions.
3. Add current-monster life-history view (`만난 날`, `첫 기록을 먹인 날`).
4. Add simple encyclopedia data model with Route A/B as same-tier siblings and one-line personality hints.
5. Keep the completed menu services covered by regression and Windows lifecycle checks.
6. Add first-run drop animation and auto-start toggle.
7. Build memory resurfacing + personality dialogue engine.
8. Add care loop and one minimal mini-game.
9. Continue accuracy/blind/regression tests in parallel.
