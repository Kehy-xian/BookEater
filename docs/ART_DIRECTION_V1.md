# BookEater Art Direction v1

## Why art starts now

The local data model, reading-feed loop, hidden growth system, book→many-notes journal, Windows packaging, and transparent desktop-pet shell are stable enough that visual work can now become part of the product rather than a disposable mockup. From this sprint onward, UI layout must be designed around the real creature silhouette instead of a temporary placeholder.

## Core visual language

**Paper + ink + scribble + bookmark.**

The creature should feel born from a reader's notes, not like a generic fantasy mascot. Avoid visual resemblance to Pokémon or any existing commercial monster IP.

- Warm ivory paper body rather than pure white.
- Near-black ink eyes and mouth.
- One muted bookmark-red accent.
- Slightly imperfect hand-drawn / printed-paper feel.
- Readable silhouette at small desktop-pet size.
- Cute, but not infantile: curious, observant, slightly strange.

## Base creature: 글씨알

### Silhouette

- Rounded egg / crumpled-page body.
- Very short feet.
- Two simple ink-dot eyes.
- Oversized mouth that visibly consumes letters.
- Bookmark tail is the strongest identifying silhouette cue.
- Two faint ruled-paper lines or swallowed glyphs may appear on the belly.

### Personality shown through motion

- **IDLE:** quiet breathing/bobbing, occasional blink, tiny look-around.
- **EAT:** squash-and-stretch, mouth opens wide, 2–3 glyph crumbs are pulled inward.
- **WALK:** small quick steps; bookmark tail lags behind slightly.
- **READ:** holds or peers into a tiny page; should feel focused rather than scholarly/stiff.
- **SLEEP:** body settles flatter; a folded-page corner can act like a blanket cue.
- **TALK:** minimal mouth change / bounce, not lip-sync.
- **SPIT_MEMORY:** a small paper scrap or glyph bubble emerges from the mouth.

## Sprite production plan

### Phase A — now

Freeze **one base character only** before drawing evolution families.

1. Concept sheet: front, 3/4, side silhouette, mouth-open, sleeping pose.
2. Choose final proportions and palette.
3. Produce transparent PNG sprites for **IDLE + EAT** first.
4. Replace the current Tk vector placeholder with sprite rendering.
5. Test at actual desktop sizes and Windows scaling levels.

Do not draw 20+ evolutions before the base creature feels good on the desktop.

### Phase B — after IDLE/EAT feels good

Add WALK / READ / SLEEP / TALK / SPIT_MEMORY. Target a compact first sheet rather than excessive animation.

Recommended first production target:

- IDLE: 4 frames
- BLINK: 2 frames (can overlay/reuse IDLE)
- EAT: 6 frames
- WALK: 4 frames
- READ: 3 frames
- SLEEP: 3 frames
- TALK: 2 frames
- SPIT_MEMORY: 4 frames

Approximately **24–28 unique frames** total depending on reuse.

### Technical sprite format

- Authoring canvas: 96×96 px per frame (or 192×192 source rendered down cleanly).
- Transparent PNG.
- Keep character feet aligned to a shared baseline.
- No baked-in shadow; desktop renderer draws shadow separately so it can adapt to scale.
- Naming: `geulssial_idle_00.png`, `geulssial_eat_00.png`, etc.
- Runtime must retain a vector fallback if sprite assets are missing/corrupt.

## Evolution art rule

Internal growth remains hidden from players, but art production can use the private two-layer model:

- Reading-response tendency controls the **main body family**.
- World/topic tendency controls **secondary mutations/accessories/patterns**.

The player sees only the resulting creature and broad narrative hints; no trait percentages, keyword recipes, or exact evolution equations are revealed.

Examples for development art only:

- thoughtful body + nature modifier → leaf-vein paper texture / small antler-like bookmark branches.
- emotional body + dark modifier → longer soft tail / ink-shadow edge.
- inquiry body + social modifier → collected ticket/tab motifs, window/grid markings.
- sensory body + imagination modifier → ribbon-like ink strokes / star-shaped punctuation.

## Palette v1

- Paper: `#F4EDDA`
- Paper shadow: `#DED3BA`
- Ink: `#25211E`
- Outline: `#29241F`
- Bookmark accent: `#B95F55`

These are working production colors, not immutable brand colors. Final art review may adjust them together, but individual UI screens should not independently invent new creature colors.

## What is intentionally not final yet

- Exact pixel-art vs hand-drawn raster finish.
- Final eye spacing / mouth proportions.
- Evolution species silhouettes.
- Decorative UI skin surrounding the pet.

Those should be decided after the first concept sheet is judged at real desktop scale.
