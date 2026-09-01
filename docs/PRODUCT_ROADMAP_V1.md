# BookEater Product Roadmap v1

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

### Book journal
- Books are registered once and can have many chronological reading notes.
- Title is required; author is optional for manual entry.
- Optional progress text (page/chapter/etc.) is stored separately from the note text so it does not contaminate NLP.
- Recently read books are shown first.
- Same book can receive repeated notes over days/weeks.
- Book timeline view is available locally.

### Desktop pet shell
- Transparent small window on Windows.
- Always on top.
- Drag to move.
- Double click opens reading-record entry.
- Right click menu currently exposes record entry, book-record view and exit.
- Vector placeholder has IDLE and EAT animation.
- Production art contract exists for idle/eat/walk/read/sleep/talk/spit_memory sprite states.

### Windows build
- PyInstaller one-folder Windows build.
- Bundled ONNX model/tokenizer verified in CI.
- Packaged runtime smoke verifies model loading and local SQLite creation.

## Next implementation: desktop-pet experience

### 1. Production character art
- Lock the base creature `글씨알` visual direction first.
- Generate/review 3 concept variants, then approve one canonical silhouette.
- Make production sprite assets for IDLE and EAT first, then WALK/READ/SLEEP/TALK/SPIT_MEMORY.
- Left/right movement may mirror one side-facing sprite; front/back views are not mandatory unless an interaction needs them.
- Evolution forms reuse the same state contract so art can be added without changing NLP/database logic.

### 2. Player-facing pet menu
Target menu:
- 기록 먹이기
- 내 서재
- 기억 꺼내기
- 돌보기
- 몬스터 도감
- 설정
- 종료

### 3. Personality and dialogue engine
- Pet personality is derived from long-term hidden growth history, not exposed labels.
- Dialogue tone changes gradually with the formed personality.
- Dialogue sources:
  1. generic personality lines,
  2. resurfaced reading memories,
  3. commentary on a resurfaced memory,
  4. book recommendations based on accumulated reading history,
  5. context lines for care, sleep, reading and idle states.
- Avoid claiming a memory or recommendation was caused by a specific hidden keyword.

### 4. Memory resurfacing
- Retrieve past local notes using local semantic search.
- `기억 꺼내기` can surface a past note, book title, date/progress context and a short pet reaction.
- Future quiz mode can build deterministic questions from the user's own notes.

### 5. Recommendations
- Recommend only real catalog/API candidates; never invent book titles.
- Two hidden ranking intents remain available internally: taste-deepening and breadth-expanding.
- Player-facing explanation is natural-language and broad, not a trait-score report.

### 6. Auto-start option
- Windows per-user startup toggle, default OFF.
- Store setting locally.
- Prefer HKCU per-user startup or an equivalent no-admin mechanism.
- Setting can be turned on/off at any time.

### 7. First-run drop animation
- On the first-ever successful launch, the pet drops from above the visible work area and lands with a small bounce (`콩`).
- Persist a local `intro_seen` flag so it does not replay every boot.
- Provide an optional `인트로 다시 보기` setting later.

### 8. Care loop and mini-games
Care is deliberately separated from reading genetics.
- 밥주기: affects satiety/mood, not reading evolution.
- 놀아주기: affects mood/bond.
- 씻기기: affects cleanliness/mood.
- Simple mini-games may improve bond and trigger dialogue/animations.
- No death, irreversible punishment or forced daily streaks.
- Soft needs may decay slowly, but neglect must not erase reading progress.

### 9. Monster encyclopedia / collection
- Encyclopedia records every form the user has actually encountered.
- Unknown forms remain silhouettes/locked entries.
- To make multiple evolution lines genuinely collectible, a later loop is needed: a fully grown monster can be archived to the user's `서고`, then the user may raise a new `글씨알` while keeping previous monsters in the collection.
- Never overwrite or delete the history of a retired/archived monster.

## Art production scope

Do not draw every evolution from every angle up front.

For the first production milestone:
- Base `글씨알`: canonical design sheet + IDLE 4 + EAT 6.
- After desktop-size readability is approved: WALK 4 + READ 3 + SLEEP 3 + TALK 2 + SPIT_MEMORY 4.
- Left/right can be mirrored unless asymmetrical visual modifiers require dedicated frames.
- Back view is optional, not a requirement for every form.

For evolution lines:
- Each form needs a canonical silhouette and the states actually used by the game.
- Reuse motion templates where practical.
- World/theme modifiers should be modular visual motifs where possible, rather than redrawing every 4×5 combination as a completely independent full sprite set.

## Data safety / update rules
- User books, notes, corrections, monster history, settings, encyclopedia unlocks and archived monsters are user data and must never be overwritten by app updates.
- Model/app updates can add new analysis versions but may not silently rewrite past user corrections or past monster history.
- Care state may evolve over time, but reading/evolution history is permanent unless the user explicitly resets it.

## Near-term order
1. Approve `글씨알` art direction and production sprite style.
2. Integrate production IDLE/EAT sprites into the transparent desktop pet with vector fallback.
3. Finish menu shell: 내 서재 / 기억 꺼내기 / 설정 placeholders backed by real local services.
4. Add first-run drop animation and auto-start toggle.
5. Build memory resurfacing + personality dialogue engine.
6. Add care loop and one minimal mini-game.
7. Add encyclopedia and archived-monster data model.
8. Continue accuracy/blind/regression tests in parallel.
