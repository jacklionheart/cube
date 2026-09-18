# Codebase review and shared-code proposal — 2026-09-18

Scope: every Python file in `roto/`, `samp-roto/`, `17lands/`, and
`cubecobra/` (plus the notebook builders), with the roto/samp-roto twins
diffed line-by-line. Part A is the review, severity-ranked, each finding
verified against the actual data flow. Part B is the `cubelib/` design
with the concrete duplication it would replace and a migration order that
keeps both publish pipelines working at every step.

Companion change (separate commits on this branch): the blog platform was
extracted to `etude/` and `roto/blog.py` reduced to a wrapper, verified
byte-identical (see `etude/README.md`).

---

## Part A — Technical review

Severity scale: **P1** wrong output or crash on a supported path today ·
**P2** wrong/lost data on a realistic near-future path, or missing safety
around shared live artifacts · **P3** fragility, drift, dead code ·
**P4** hygiene.

### P1 — broken or wrong today

**A1. `samp-roto/packages.py` CLI is dead: `load()` is a stale roto copy.**
`samp-roto/packages.py:39-55` still loads
`sources/draft{1..3}.xlsx` ("Parse the three source drafts"), but samp's
sources are slugified pod names (`mockingbird.xlsx`, …, per
`samp-roto/refresh.py:28-46,60-72`); `draft1.xlsx` never exists there, so
`python3 samp-roto/packages.py` (any flag) dies in `load()` with
FileNotFoundError. Only the library functions survive, imported by
`samp-roto/roto_summary.py:482` — meaning every CLI mode advertised in
the module docstring (`--null`, `--straddles`, `--relax`, `--loose`,
`--mermaid`) is unreachable on the samp side. Either port `load()` to the
samp source map or delete the CLI and docstring.

**A2. Partial-signature agreement counts shared *absence* as agreement.**
samp's `_signature_groups` (`samp-roto/packages.py:82-97`) deliberately
admits partial signatures (tuples containing `None`) — right call for 13
pods. But `package_edges` (`samp-roto/packages.py:100-110`) was not
updated: `if a == b` is true for `None == None`, so two packages that
were both simply *absent* from the same pod count as "agreeing in that
draft". Consequences: a pair of packages that co-occurred in one deck in
one pod but happen to be co-absent from exactly one other pod satisfies
`agreement == 2` and gets an edge; `components()` then chains these into
fake archetype clusters, and `report()` prints "same deck in draft [k]"
for drafts in which neither package existed. roto is unaffected only
because its signatures are always full. Fix: `a is not None and a == b`.
(Same latent issue in the blog/report satellite logic is *not* present —
`roto/blog.py` ran on full signatures.)

**A3. `samp-roto/lane_compare.py` skips pick canonicalization — the
"Stomping ground 2" class of bug.** The main pipeline canonicalizes
hand-typed picks against the cube list, case-insensitively and with a
substring fallback (`samp-roto/roto_summary.py:989-1009`), and patches
`" 2"`-suffixed duplicate lands into their base card's deck zone
(`samp-roto/roto_summary.py:1021-1030`). `lane_compare.load_data`
(`samp-roto/lane_compare.py:88-121`) does **neither**: it takes
`parse_draft` picks raw. Verified failure modes:

- A hand-typed pick like `"Stomping ground 2"` (lowercase) never matches
  `deck.get(card)`; the fallback at `lane_compare.py:108-110`
  (`deck.get(card[:-2].strip())`) is exact-case, so the base lookup
  against the canonical `"Stomping Ground"` key also fails → the card
  silently vanishes from that deck's maindeck in the report.
- Any pick-name variant absent from `scryfall.json` (the file is keyed by
  the cube list's exact strings — `samp-roto/scryfall.json` holds
  `"Stomping Ground 2"`, 20 suffixed entries total, no lowercase keys)
  sails through `is_land` (`lane_compare.py:41-44`: `scry.get(name)` →
  `None` → `bool(info)` is False → "not a land") and a **land leaks into
  the nonland lane analysis** and shows up in the rendered report; it
  likewise renders no image in `card_grid` (`:185-191` silently skips
  missing images), so it appears only in the variant text lists — exactly
  the reported symptom.

Fix pattern (belongs in shared code, finding B-2): canonicalize
`casefold()` + strip trailing `" \d+"` against the cube list *before*
any deck/scryfall lookup, then apply the land filter; make `is_land`
raise (or warn) on unknown names instead of defaulting to nonland.

**A4. `" 2"`-suffix handling is exact-case and copy-2-only.**
`samp-roto/roto_summary.py:1024-1030` (`card.endswith(" 2")`,
`base = card[:-2]`) misses `" 3"` and any case variant;
`samp-roto/rtb_to_xlsx.py:41-50` (`dedupe_names`) appends `" 2"` even for
a *third* copy (name already in `seen` → still becomes `"Name 2"` again),
which then trips the "picked twice" warning in `parse_draft`
(`samp-roto/roto_summary.py:101-103`) and silently drops the earlier
pick; the Cube tab writer (`rtb_to_xlsx.py:80-81`) emits only `"Name 2"`
regardless of `maxCopiesInDraft`. Harmless with today's max of two
copies; wrong the first time a cube runs 3× of anything.

### P2 — data-loss / safety around the live Sheets, near-future breakage

**A5. Publishing overwrites the live shared Sheets with no backup and no
default verification.** Both `refresh.py` `main()`s
(`roto/refresh.py:114-143`, `samp-roto/refresh.py:142-174`) publish **by
default** — `--dry-run` and `--verify` are opt-in — via
`drive.files().update` which replaces the entire spreadsheet content in
place (`roto/upload_sheet.py:49-62`). Guards that exist: `--verify`
round-trips the formula build through a temp Sheet and diffs computed
tabs cell-by-cell (good, and the temp sheet is deleted in a `finally`);
`check_deck_coverage` warns on unreliable maindeck inference; hardcoded
`TARGET_SHEET_ID` avoids fat-finger targets. What's missing, compared to
the repo's own best practice in `cubecobra/cc.py:271-284` (auto-backup
before every mutation, optimistic version locking):

- no snapshot/export of the live sheet before overwriting it — a refresh
  run against corrupted sources destroys the shared artifact with only
  Google's version history as recourse;
- verification is not on by default (and its fuzzy tolerance of `0.051`
  **absolute** on any column whose header contains "Avg"/"Win Rate"
  (`roto/refresh.py:32,93-105`) would also mask a genuine 5-point
  win-rate regression);
- failures surface as bare `assert` (`refresh.py:91`) rather than a
  diagnostic;
- nothing checks that the freshly downloaded sources parse to sane shapes
  (e.g. non-empty Matches, expected player counts) before the pipeline
  ships them.

**A6. `urllib` fetch inside `load_decks` on a machine where urllib SSL is
known-broken.** `roto/roto_summary.py:229-231` and
`samp-roto/roto_summary.py:255-257` fall back to
`urllib.request.urlopen` for any pool missing from `deckcache/`. The
repo's own comments say this python's urllib SSL is broken
(`roto/refresh.py:48`), which is why `refresh.py` curl-prefetches
(`roto/refresh.py:47-58`, `samp-roto/refresh.py:75-86`). Every *other*
entry point — `roto_summary.py` run directly, `packages.py`, `blog.py`,
`report.py`, `lane_compare.py`, `build_decks_tsv.py` — hits the urllib
path the moment a new `decks.tsv` row exists without a prefetch, and
crashes (also: no User-Agent, no rate limiting if it *did* work). The
curl helper is meanwhile re-implemented five times (see B-1).

**A7. Hardcoded season/shape constants that break on the next draft.**
- `roto/packages.py:44` `for i in range(1, 4)` and `f"Draft {i}"` — a
  fourth LoL draft means editing the library, not data.
- `roto/report.py:588` `sum(...) == 3` (drafts count), plus prose
  constants ("34 lane-cards", "p = .003", "28 players") baked into
  strings at `roto/report.py:646-655` with no assert tying them to the
  computation (the blog's components, by contrast, assert their prose
  numbers — that pattern should be copied here).
- `samp-roto/packages.py:286-289` `MIN_PAIR_CORE = 12` with a comment
  calibrated to "11 known-deck pods"; now 13/13 decks are known, the
  threshold's rationale is stale.
- `samp-roto/roto_summary.py:42` `DOUBLE_PICK_AFTER = 25` is global to
  all 13 pods — correct this season, but it's a per-draft rule encoded as
  a module constant, and the Sheets formula copy of the same math
  (`samp-roto/roto_summary.py:692-699`) must be kept in sync by hand.
- `samp-roto/lane_compare.py:12` docstring says component lanes use
  ">= 6 shared drafts"; `main()` passes `K=7` (`:323`). Header strings
  hardcode "of the 13 decked drafts".

**A8. Silent tolerance of missing scryfall data is inconsistent — some
paths crash, some silently mislabel.** `roto/packages.py:265-273`
(`is_land`, `nonland_owners`) and `roto/report.py:377` index
`scry[name]` directly → KeyError the first time a cube list drifts ahead
of the cached `scryfall.json`; `samp-roto/lane_compare.py:41-44` and
`colors_of` (`:178-182`) treat missing as "colorless nonland" (see A3);
`samp-roto/fetch_images.py:49-50` silently drops cards with no image.
Pick one behavior (fail loudly with the card name) in shared code.

### P3 — drift between the twins, fragile constructs, dead code

**A9. The twins, characterized.** `diff` sizes: `packages.py` 76 changed
lines, `roto_summary.py` 368, `refresh.py` 65, `upload_sheet.py`
**byte-identical**. Who's newer/better where:

| Area | roto | samp-roto | Verdict |
|---|---|---|---|
| `card_colors` | mana + land-produced + **flashback** (`roto/packages.py:211-230`) | no flashback (`samp-roto/packages.py:217-231`) | roto newer; backport to samp |
| `signature_groups` | full signatures only (`roto/packages.py:81-91`) | partial signatures + `MIN_SHARED_DRAFTS` (`samp:82-97`) | samp newer; parameterize (roto = "min shared drafts = n_drafts") |
| `flex_packages` | assumes 3 live drafts (`roto/packages.py:319-337`) | generalized to live-draft subsets (`samp:322-343`) | samp newer; strictly subsumes roto's |
| `pair_packages` | `MIN_PAIR_CORE = 5` | `= 12` + rationale comment | same code, per-project constant |
| `unique_ensembles` | present (`roto/packages.py:376-411`) | **missing** | roto-only; belongs in shared core |
| `--nonland` CLI flag | present (`roto/packages.py:513-514`) | missing | roto newer |
| avg rounding | `round()` = banker's (`roto/roto_summary.py:652-653`) | `round1()` half-away-from-zero matching Sheets ROUND (`samp:45-48,669-670`) | samp newer; roto's values-vs-formulas verify only passes because of the 0.051 fuzz |
| pick canonicalization in `main()` | exact casefold only (`roto/roto_summary.py:956-965`) | + unique-substring fallback + grid rewrite (`samp:989-1009`) | samp newer |
| deck-name aliases | none | `DECK_CARD_ALIASES` (`samp:219-222,234`) | samp newer |
| Win Rates layout | summary columns after per-draft blocks (`roto:805-874`) | summary first, `FIRST_DRAFT_COL = 13` (`samp:829-904`) | deliberate divergence (13 pods), needs a layout parameter, not a fork |
| overall pick | plain snake (`roto:75-83`) | `overall_pick` with double-pick traversals (`samp:51-58`) | deliberate divergence, strategy parameter |
| package sheet tabs | `build_md_together` + `build_package_tabs` (`roto:451-553`) | `build_packages` frequent-itemset miner (`samp:474-569`) | different analyses; both belong in shared core |
| draft naming | positional `Draft {i}` | `name=path` specs (`samp:974-977`) | samp newer |
| scryfall cache tooling | none committed — `roto/scryfall.json` embeds `image` but the script that made it isn't in the repo | `fetch_scryfall.py` + `fetch_images.py`, separate `images.json`, **no** `image` in scryfall.json | both incomplete; two incompatible cache schemas for the same concept |

Docstring drift: `samp-roto/packages.py` module doc and `null_model`/
`flex_packages` docs still describe "2 of 3 drafts"/"the three source
drafts" (`samp:1-26,299-330`).

**A10. Dead code duplicated in both twins.** `build_pick_value` —
~107 lines each (`roto/roto_summary.py:342-448`,
`samp-roto/roto_summary.py:365-471`) — is called from **neither**
`build_workbook` (call sites: `roto:736-739`, `samp:760-762`). It also
contains the only remaining reference to a "Pick Value" tab; delete or
re-wire, but not twice. Also dead: `lane_compare.py:240-243` (a loop that
does nothing), `blog`'s `lane_by_colors`/`lane_block` and
`canon_key` (unused — now noted in the etude migration),
`roto/packages.py:191-198 late_first_pick` has no caller in the repo
(notebook-only? none found), `BASIC_COLORS` (`roto/packages.py:202`)
unused on both sides.

**A11. Verify/upload logic duplicated wholesale.**
`upload_sheet.py` is byte-identical in both projects (74 lines);
`verify()` is a 51-line identical block in both `refresh.py`s
(`roto:61-111`, `samp:89-139`); `prefetch_pools` and `curl` likewise
(`roto:35-58`, `samp:56-86`). Any fix (e.g. A5's backup-before-publish)
currently has to land twice.

**A12. `build_decks_tsv.match` is greedy prefix matching.**
`samp-roto/build_decks_tsv.py:83-92` accepts the *first* roster name
where either normalized string startswith the other — "Sam" would match
"Samantha" and vice versa; correctness today rests on the hand `ALIASES`
table and small rosters. It also assumes the Discord scrape is
chronological to infer `initial` vs `rebuild` (`:111-114`) — true of the
current export, undocumented as a requirement.

**A13. Type-line parsing is split-personality.** `companion_ok`'s local
`is_land` splits on `" — "` (`roto/roto_summary.py:167-168` and samp
`:187-188`), so an MDFC like "Bala Ged Recovery // Bala Ged Sanctuary"
(`Sorcery // Land`) counts as a *land* for Obosh/Gyruda/Keruga parity
checks, while `packages.is_land` (`roto/packages.py:265-267`) counts the
same card as *nonland*. One of these is wrong for any given companion
ruling; they should at least be the same function with a documented
choice.

**A14. Minor fragilities.**
- `load_themes` (`roto/packages.py:241-252`): `card, theme =
  line.split("\t")` → ValueError on a third column or stray tab.
- `parse_draft` requires the `Matches` sheet to exist (`roto/roto_summary.py:87`)
  — a pod sheet without one crashes rather than yielding 0-0 records.
- `refresh.verify` compares only `COMPUTED_TABS`; data tabs (Decks,
  Records) are trusted unchecked — fine, but undocumented.
- `samp-roto/refresh.py:45-49`: `slugify` defined mid-constants with the
  target-sheet comment awkwardly attached; cosmetic but it has already
  confused a merge once (comment placement).
- Empty-deck pools (e.g. `samp-roto/deckcache/b8A18D76Ju.json`, all cards
  in `sideboard`, `deck: []`) yield `main_sizes == 0`; the only guard is
  the `check_deck_coverage` warning — acceptable because rebuild links
  supersede, but a pipeline-level "0-card maindeck used for analysis"
  error would be safer than a stderr warning nobody reads under 13 pods
  of output.

### P3 — 17lands and cubecobra (briefly: these are in better shape)

**A15. `17lands/lib17` is what roto/samp should look like** — a real
package with a format registry and shared cell builders ("formerly
duplicated across five scripts", `lib17/data.py:1-2`). Remaining nits:
- `fetch.card_ratings` (`lib17/fetch.py:25-58`) targets the legacy
  endpoint that `card_data`'s own docstring calls "a stub that returns
  near-zero counts" (`:64-73`); it has no remaining in-repo caller —
  delete it or make it warn, before someone trusts it again.
- `fetch.py` uses `requests` (certifi ships its own CA bundle,
  `_download` comment `:120-124`) — i.e. the 17lands side already solved
  the broken-urllib problem *without* curl; the roto projects use curl
  because they run on the system python without deps. The shared library
  should encode this decision once (see B-1).
- `bangers_sheet.py:81-82` fetches the `top` cohort even for sets that
  will turn out to have none (wasted call, though cached); the
  pre-2022 all-players fallback in `lib17/bangers.py:110-118` is correct.
- `data.FORMATS` table windows are hand-maintained dates
  (`lib17/data.py:16-27`) — fine, documented.

**A16. `cubecobra/` is the repo's reference standard**: optimistic
version locking, backup before every mutation, never-replay-on-timeout
recovery (`cc.py:297-341`), index-safety invariants with refusal paths
(`cc.py:91-127`), dry-run by default with `--apply` (`elemental.py`,
`fantasia.py`, `gaelaria.py`), and actual unit tests (`test_cc.py`,
`test_tag_library.py`, `test_fantasia.py`). The one wart:
`gaelaria.py:106-107` runs `fetch.sh` with `check=False`, so a failed CSV
refresh after a successful sync is silent.

**A17. Repo hygiene.** Root `README.md` documents `cubecobra/` and
`17lands/` but not `roto/`, `samp-roto/` (nor, until this branch,
`etude/`). There are no tests outside `cubecobra/`. `upload_sheet.
find_client_secret` globs `~/Downloads/client_secret*.json`
(`roto/upload_sheet.py:27-31`) — machine-specific magic that will
mystify any second machine.

### Top 5, if only five get fixed

1. A2 (samp partial-signature edges count co-absence — wrong analysis
   output today).
2. A3/A4 (canonicalization: lane_compare misses picks / lands leak; the
   `" 2"` handling is exact-case, copy-2-only — the shared
   `casefold + strip " \d+"` canonicalizer fixes the whole class).
3. A5 (live-Sheet publish has no backup and opt-in verification).
4. A1 (samp packages CLI dead — stale copy of roto's loader).
5. A6 + B-1 (kill the urllib fallback; one curl-based fetch layer with
   UA + rate limiting instead of five copies).

---

## Part B — Shared-code proposal: `cubelib/`

A top-level `cubelib/` package, imported by both roto projects (and
optionally 17lands/etude for the pieces they share). Constraints
honored: system python3 + openpyxl only (no new hard deps for the roto
pipelines), curl for network (A6), behavior-preserving migration.

```
cubelib/
  __init__.py
  net.py          # curl-based HTTP with UA + rate limit
  names.py        # canonicalization
  colors.py       # color rules, is_land, guild names
  scryfall.py     # batched card metadata + image cache
  sheets.py       # Google Sheets upload / verify / backup
  xlstyle.py      # openpyxl styling helpers
  rotolib/
    __init__.py
    draft.py      # Pick/Draft, parse_draft, pick-order strategies
    decks.py      # decks.tsv + sealeddeck pools + companions
    packages.py   # the signature/package analysis core
  tests/
```

### B-1 `cubelib/net.py`

`curl(url, out=None, *, headers=(), post_json=None, retries=...)` plus a
module-level `sleep_between` (0.3 s Scryfall / 3 s 17lands style) and the
shared User-Agent (`cube-analysis/1.0 (jack@loopflow.studio)`). Keep
curl subprocesses (urllib SSL broken on the system python; 17lands runs
under uv with `requests` and can keep doing so — document both in the
module docstring so the decision lives in one place).

Replaces:
- `roto/refresh.py:35-37` and `samp-roto/refresh.py:56-58` (`curl`),
- `roto/refresh.py:47-58` / `samp-roto/refresh.py:75-86`
  (`prefetch_pools` — becomes `decks.py`'s job via net),
- `samp-roto/fetch_scryfall.py:44-51` and `samp-roto/fetch_images.py:17-23`
  (curl POST with UA),
- `samp-roto/rtb_to_xlsx.py:34-36`,
- **and the urllib call inside both `load_decks`**
  (`roto/roto_summary.py:229-231`, `samp-roto/roto_summary.py:255-257`) —
  fixing A6.

### B-2 `cubelib/names.py`

- `norm(name)` — casefold + accent-strip
  (today `roto/roto_summary.py:191-196` ≡ `samp-roto/roto_summary.py:211-216`).
- `strip_copy_suffix(name)` → `re.sub(r"\s+\d+$", "", name)` (today in
  four places: `samp-roto/fetch_scryfall.py:39-41`,
  `samp-roto/fetch_images.py:13-14`, ad-hoc `card[:-2]` at
  `samp-roto/roto_summary.py:1024-1030`, `endswith(" 2")` hacks at
  `samp-roto/lane_compare.py:48,107-110`).
- `Canonicalizer(cube_names, aliases={})` building a lookup with:
  casefold key, split-card front-half key (`roto/roto_summary.py:206-207`
  ≡ `samp:232-234`), alias table (`samp:219-222`), and
  `resolve(raw) -> (canonical, how)` implementing
  **casefold exact → casefold-with-copy-suffix-stripped (+ re-suffix) →
  unique-substring fallback** (`samp-roto/roto_summary.py:995-1000`).
  This is the single fix point for A3/A4: `lane_compare`, both
  `roto_summary.main`s, and `packages.load` all call the same resolver.

### B-3 `cubelib/colors.py`

- `card_colors(name, scry)` — mana-cost colors + land-produced (unless
  5-color) + **flashback cost colors** — the roto version
  (`roto/packages.py:211-230`); replaces samp's flashback-less copy
  (`samp-roto/packages.py:217-231`).
- `colors_str`, `WUBRG`, canonical color-combo order (`CANON` in
  `etude/etudelib/render.py:110-117`, ex-`roto/blog.py`).
- `is_land(name, scry, *, strict=True)` — one definition (front-face
  `" // "` split, `roto/packages.py:265-267`), raising on unknown names
  by default (A8); `companion_ok` adopts it with an explicit
  `front_face=False` variant if the em-dash semantics are actually wanted
  (A13 — decide once, in a docstring).
- `GUILDS` names (`roto/report.py:100-107` ≡ `samp-roto/lane_compare.py:27-34`).

### B-4 `cubelib/scryfall.py`

`fetch_cards(names, fields=..., images=True) -> dict` — batched
`/cards/collection` POSTs of 75 via `net.curl`, keyed by the **cube's
exact names** (copy-suffixed keys share the base card's record), with
front-half fallback for split/room cards and face-union for colors, plus
`image` extracted from `image_uris` / first face. One cache schema:
`scryfall.json` including `image` (roto's format), superseding samp's
split `scryfall.json` + `images.json`.

Replaces: `samp-roto/fetch_scryfall.py:1-100`,
`samp-roto/fetch_images.py:1-57`, and *creates* the missing tool that
produced `roto/scryfall.json` (which embeds `image` but has no generator
in the repo — currently unregenerable). `17lands/lib17/fetch.py:147-181`
(bulk oracle dump) stays separate: different scale, different tool.

### B-5 `cubelib/rotolib/draft.py`

`Pick`, `Draft` dataclasses; `parse_draft(path, name, *,
pick_order=snake)` where `pick_order` is a strategy: `snake(n)`
(`roto/roto_summary.py:75-83`) or `double_after(25)`
(`samp-roto/roto_summary.py:51-58` + grid loop `:93-104`); Matches
parsing (`roto:86-96` ≡ `samp:106-116`) tolerant of a missing sheet
(A14). Also owns `round1()` (Sheets-compatible rounding,
`samp-roto/roto_summary.py:45-48`) so roto picks it up (A9 rounding row).
The Sheets *formula* for overall pick stays in the per-project workbook
layer but is generated from the same strategy object so the two
implementations can't drift (A7).

### B-6 `cubelib/rotolib/decks.py`

`load_decks(tsv_path, cube, *, canonicalizer, scry)` +
`companion_ok` + `COMPANIONS`/`BASICS`/`MAIN_ZONES`/`PERMANENT_TYPES` +
`check_deck_coverage`. Today this block is duplicated essentially
verbatim: `roto/roto_summary.py:142-261,556-575` ≡
`samp-roto/roto_summary.py:162-288,573-592` (samp adds
`DECK_CARD_ALIASES`, which becomes a `Canonicalizer` argument). Pool
fetch goes through `net.curl` with cache-dir injection; add the
"0-card maindeck" hard warning (A14).

### B-7 `cubelib/rotolib/packages.py` — the analysis core

Parameterized by the draft list itself (no `range(1, 4)`); key API:

- `maindeck_owners(drafts, cube, decks)` (identical twins:
  `roto/packages.py:58-69` ≡ `samp:58-69`).
- `signature_groups(owners, *, min_size=3, min_shared=None)` —
  `min_shared=None` ⇒ full signatures (roto, `roto/packages.py:81-91`);
  an int ⇒ samp's partial signatures (`samp:82-97`). One function, two
  documented modes.
- `package_edges(groups, agreement=2)` with the **None-safe** comparison
  (fixes A2) — identical otherwise (`roto:94-104` ≡ `samp:100-110`).
- `components`, `co_maindeck_counts`, `halos`, `loose_components`
  (identical twins, `roto:107-173` ≡ `samp:113-179`).
- `pair_packages(owners, min_core)` (`roto:286-316` ≡ `samp:289-319`;
  the constant moves to per-project config).
- `flex_packages` — samp's generalized version (`samp:322-343`), which
  reduces to roto's (`roto:319-337`) when all signature entries are live.
- `team_partners`, `straddles` (identical, `roto:340-360` ≡ `samp:346-366`).
- `unique_ensembles` (roto-only, `roto/packages.py:376-411`).
- `null_model` (identical, `roto:414-445` ≡ `samp:382-413`).
- `frequent_sets(card_decks, min_support, min_size)` — the maximal
  co-maindeck itemset miner currently written **twice** on the samp side:
  `samp-roto/roto_summary.py:474-569` (`build_packages`' `dfs`/
  `is_maximal`) and `samp-roto/lane_compare.py:128-153` (`mine`).
- `never_drafted`, `never_maindecked`, `late_first_pick` (identical).

Project-side `packages.py` files become thin: a loader (per-project
sources), per-project constants (`MIN_PAIR_CORE`), re-exports, and the
CLI — which fixes A1 by construction (the samp loader loads samp
sources).

### B-8 `cubelib/sheets.py`

- `get_credentials()` / `upload(path, title, file_id=None)` — the
  byte-identical `upload_sheet.py` twins (`roto/upload_sheet.py:1-75` ≡
  `samp-roto/upload_sheet.py:1-75`).
- `verify(formulas_x, values_x, tabs, fuzzy_headers)` — the identical
  51-line block (`roto/refresh.py:61-111` ≡ `samp-roto/refresh.py:89-139`),
  with a real error report instead of `assert`, and a *relative* fuzz for
  percent columns (A5).
- **New:** `snapshot(file_id, dest_dir)` — export the live sheet to
  `out/backups/<timestamp>.xlsx` before `update` (drive `export_media`,
  same call `verify` already uses), and `publish(...)` that composes
  snapshot → (verify) → update. This is the cubecobra
  backup-before-mutation discipline (`cubecobra/cc.py:271-284`) applied
  to the Sheets pipelines, closing A5. `refresh.py` keeps only the
  per-project SOURCES table, download loop, and flags.

### B-9 `cubelib/xlstyle.py`

`COLOR_FILLS`, `HEADER_FILL/FONT`, `CARD_FONT`, `CENTER`, `color_fill`,
`style_card_cell`, `style_header` (`roto/roto_summary.py:111-140` ≡
`samp:131-160`), plus the two recurring `ColorScaleRule` recipes (pick
heat: `roto:714-733` ≡ `samp:738-758`; 0–.5–1 win-rate scale, four
occurrences per file). `build_workbook` itself stays per-project — the
Win Rates column layout genuinely differs (A9) — but both are built from
these helpers plus `rotolib`.

### Migration order (both pipelines green after every step)

Each step ends with: `python3 roto/refresh.py --dry-run` and
`python3 samp-roto/refresh.py --dry-run`, diffing the `--values` builds
against the prior step's output (byte-comparison of extracted sheet
values, same trick as `verify`), plus `python3 roto/blog.py` diffed
against `out/blog-post.html`.

1. **`cubelib/net.py` + `names.py`** (+ `tests/`). Point
   `prefetch_pools` and the `load_decks` urllib call at `net.curl`
   (A6); adopt `Canonicalizer` inside `lane_compare.load_data` (A3) and
   both `roto_summary.main`s. Output-affecting only where A3/A4 bugs
   fired — inspect those diffs by hand, they are the fix.
2. **`sheets.py`**: move `get_credentials`/`upload`/`verify` in; both
   `upload_sheet.py`s become import-shims (CLI preserved); add
   `snapshot` and wire `refresh.py` to snapshot-before-update. No output
   change; publish path gains the backup.
3. **`colors.py` + `scryfall.py`**: samp regenerates one unified
   `scryfall.json` (with images); `lane_compare`/`roto_summary` read via
   cubelib; delete `fetch_images.py`/`images.json` once diffed. samp's
   `card_colors` gains flashback — expected diffs only in color strings
   for flashback cards; review them.
4. **`rotolib/draft.py` + `decks.py`**: roto first (default snake), diff
   workbook; then samp with the `double_after(25)` strategy, diff. roto
   adopts `round1` here — the values build changes on .X5 averages and
   now *matches Google's evaluation*; run `--verify` once to confirm the
   fuzz is no longer doing the work.
5. **`rotolib/packages.py`**: roto's `packages.py` re-exports from
   cubelib (blog/report/notebooks import paths unchanged); then samp's,
   with a working samp loader (A1) and the None-safe `package_edges`
   (A2 — CLI output changes are the fix). `build_packages` and
   `lane_compare.mine` switch to `frequent_sets`; diff the Teams tabs.
6. **Cleanup**: delete `build_pick_value` from both (A10), stale
   docstrings (A9), `lane_compare` dead loop; update root README; port
   the report.py prose constants to asserts (A7).

### Testing

`cubelib/tests/` under plain `unittest` (matching `cubecobra/test_*.py`;
no new deps): names (canonicalizer table-driven cases incl.
`"Stomping ground 2"`), colors (flashback, rainbow lands, MDFC land),
packages (a 3-deck / 13-deck toy fixture exercising full + partial
signatures, the None-agreement regression, flex/pair/ensemble), sheets
`verify` against two tiny in-memory workbooks, and a golden-file test of
`etude`'s `render_doc` dialect. The blog components' prose asserts stay
as the integration net.

### What deliberately stays duplicated

- Per-project `refresh.py` SOURCES tables, sheet IDs, tab lists.
- `build_workbook` sheet layouts (genuinely different products).
- `rtb_to_xlsx.py`, `build_decks_tsv.py` (samp-season-specific), though
  both should adopt `names.strip_copy_suffix`/`norm`.
- 17lands' `requests`-based fetch (uv-managed env; documented in
  `net.py`).
