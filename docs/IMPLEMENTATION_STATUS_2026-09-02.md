# BookEater implementation status — refreshed 2026-09-03

This file is the current repository-backed status. The first public prerelease is
`v0.1.0-beta.1`. `PRODUCT_ROADMAP_V1.md` records the earlier product direction and is no longer a
reliable checklist by itself.

## Product constraints that remain binding

- Local/offline reading archive and growth state by default.
- One book may own any number of chronological reading records; continuation never overwrites an
  earlier record.
- Submitted text is saved before analysis. Unsubmitted text autosaves locally and is recoverable.
- RESPONSE and WORLD are independent nullable multi-label layers. `사회` is a WORLD label; no
  forced 4×5 matrix and no generic `기타` trait.
- Player UI does not reveal classifier scores, exact thresholds, keywords or evolution recipes.
- Recommendations may use only real catalog candidates. Reading text and local growth history do
  not go to the catalog service.
- Improvement sharing is separate, explicit, off by default and minimal. No desktop upload is
  implemented yet.
- Installer/update/uninstall operations may replace program files but never silently overwrite
  books, records, settings, corrections, backups, encyclopedia history or growth history.

## Implemented and regression-covered

### Reading, storage and safety

- Local SQLite runtime, one-book-to-many-record journal and recent-book ordering.
- Save-first feed submission, pending analysis retry and atomic growth commit.
- 1.2-second throttled local draft autosave, recovery and submit-time clearing.
- Portable `.bookeater-seed` export, validated planting, pre-operation backup and explicit reset.
- App-version transition backup before store/schema initialization; automatic retention of the
  newest five version backups.
- In-place installer upgrade/uninstall E2E preserving the live DB, backup and user data directory.
- Profile-scoped Windows named mutex for every interactive launch path.

### Analysis and growth

- Bundled multilingual E5 ONNX model with lexical/hybrid safeguards.
- Nullable RESPONSE/WORLD analysis, including WORLD `사회`, auxiliary uncovered-domain tags and
  conservative abstention.
- Hidden nutrition projection, recent-trajectory state, permanent lineage and delayed evolution
  when evidence is weak.
- Starter plus approved A/B/C and A1/A2/B1/B2/C1/C2 production sprite contracts; unapproved final
  forms inherit the nearest approved ancestor rather than exposing invented art.

### Player experience

- Transparent always-on-top draggable Windows pet with floor roaming, edge bump and drag-drop fall.
- Sprite IDLE/EAT/WALK/READ/SLEEP/TALK/SPIT_MEMORY plus optional
  SNACK/DELICIOUS/PLAY/WASH/BUMP/DROP replacement states and lineage-safe fallback. Every major
  visible action can be replaced independently with a complete validated PNG set.
- Feed panel, practical bookshelf/timeline, current-monster profile and lineage-tree encyclopedia.
- Collision-safe book selectors: duplicate title/author labels use publisher, ISBN or a stable
  short local token and never overwrite another book ID in the UI mapping.
- Local memory resurfacing and broad personality dialogue.
- Optional launch drop animation, 100/75/50% size controls, tray home/restore and per-user Windows
  auto-start, default OFF.
- Care state, distinct snack/delicious/play/wash poses, post-feed delicious reaction and one
  minimal letter-catching mini-game; bond changes greeting and talk frequency but never the
  reading-derived evolution lineage.
- Real-catalog recommendation client, explicit cold-start explanation, local taste/expansion ranking
  and confirmed wishlist save.
- Catalog-first ISBN/title/author book registration with edition selection and manual fallback.
- Bookshelf title/author edit, status explanations and metadata-only deletion that preserves notes
  and already-established genetics.
- Explicit update check plus verified installer download, SHA-256 validation, second install
  confirmation and shell-free Windows launch.

### Build and operations

- Full test discovery in core CI rather than a manually maintained test-file list.
- Windows package smoke with bundled model/resources and packaged `--mutex-smoke`.
- Windows installer compile, manifest hash contract and in-place upgrade E2E.
- Version-gated GitHub Release workflow that publishes `BookEater-Setup.exe`, a matching
  `release-manifest.json` and the fixed prerelease-compatible `release-channel` manifest.
- Public `v0.1.0-beta.3` Windows prerelease; packaged smoke/mutex, installer upgrade preservation,
  public manifest and exact public installer SHA-256 validation all passed.
- Deployed Cloudflare/Aladin catalog Worker and opt-in feedback backend foundation.

## Implemented foundations but not fully enabled

- The production Aladin catalog Worker is deployed, `resources/catalog_endpoint.txt` points to it,
  and the beta.3 Windows Release passed a live catalog contract check.
- Feedback backend schema/API exists, but the desktop has no consent, correction/odd-result or
  deletion-request UI and therefore sends nothing.
- Update downloads are hash-verified, but the installer is not Authenticode-signed; Windows may
  show SmartScreen warnings.

## Not implemented

- Approved names and original production art for the 12 reserved final forms.
- Archiving a fully grown monster to a permanent shelf and raising another starter.
- Deterministic quiz mode based on the user's own notes.
- Full opt-in improvement-data lifecycle: clear consent text/version, local correction storage,
  redaction preview, upload queue/retry and deletion request.
- Authenticode signing and signed-manifest verification beyond HTTPS plus exact SHA-256.
- Multi-monitor-specific work-area handling; current roaming uses the primary Windows work area.

## Highest-priority refinement/bug risks

1. Beta.4 settings/recommendation/book-search/tray/scale flows need real Windows usability testing
   beyond headless CI, including slow network and panel-close behavior.
2. User-supplied art is validated and safely activated, but all replacement designs still require
   an actual 190×190 desktop-scale visual review before inclusion in a public installer.
3. Catalog and feedback endpoints need rate-limit, abuse and retention-policy review before public
   deployment.

## Next order

1. Run the full GitHub Windows package/mutex and installer version-upgrade regression for beta.4.
2. Redeploy the Cloudflare Worker so live ISBN-vs-keyword query routing matches this branch.
3. Publish the beta.4 Windows prerelease only after both regressions and live Worker checks pass.
4. Perform a manual Windows UI pass for animation timing, tray, scale, small panels and slow network.
5. Add explicit local correction/odd-result UX before enabling any improvement-data upload.
6. Complete multi-monitor/manual Windows playtests.
