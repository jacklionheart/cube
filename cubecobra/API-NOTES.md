# Cube Cobra automation notes

Condensed from a study of github.com/dekkerglen/CubeCobra (master @ 2026-08-27).
There is no official user API; session-cookie automation is the only route.

## Endpoints we use

| Purpose | Endpoint | Notes |
|---|---|---|
| Read cube + cards | `GET /cube/api/cubeJSON/:id` | No auth for public/unlisted. Rate limit 100/min. Accepts shortId or UUID. Contains `version` (for optimistic locking), `tagColors`, hydrated cards. |
| List my cubes | `GET /cube/api/mycubes` | Session. `{success, cubes: [{id, shortId, name}]}`. Most stable interface. |
| Login | `POST /user/login` | Form-urlencoded `username`+`password`. Always 302; success → `Location: /dashboard`. Session cookie `connect.sid`, 30-day TTL, doesn't invalidate browser sessions. No captcha/lockout. |
| Commit changes | `POST /cube/api/commit` | JSON `{id, changes, title, blog, useBlog, expectedVersion}`. 200 `{success:'true', updateApplied, version}`; 409 on version conflict (re-read, recompute, retry). `useBlog:false` → no blog/feed, changelog still written. Applied per board: swaps → edits → removes (desc) → adds (append). 50 MB body limit. |
| Delete cube | `POST /cube/remove/:id` | Session. **Hard delete, no undo.** 302 → `/dashboard` on success. No JSON variant. |
| Resolve names → printings | `POST /cube/api/getcardsforcube` | `{names: [...], defaultPrinting: 'recent'}` → card details incl. scryfall ids. No auth. |
| Tag colors | `POST /cube/api/savetagcolors/:id` | `{tag_colors: [{tag, color}]}`. Commit cards first — colors for tags on no card get filtered out. |

## Critical gotchas

1. **cubeJSON board arrays are display-sorted** (since 2026-08-26), NOT stored
   order. Every card carries `index` = its stored-array position; removes/edits
   MUST use `card.index`, never array position. Gaps in the index sequence are
   normal (null placeholder slots are filtered from the response); duplicates
   are not.
2. Never include a `nickname` field in any POST body — it's a honeypot that
   silently redirects. If CSRF is ever re-enabled upstream, all POSTs break.
3. Commit is not idempotent (adds append). Chain commits with the returned
   `version`; on 409 re-read and recompute.
4. A 403 from an authed endpoint means the session expired — re-login, don't
   treat as fatal.
5. Cube creation (`/cube/add`) requires reCAPTCHA — can't be scripted.
   (`POST /cube/quickadd` can, but caps at 2 empty cubes.)
6. Tags are plain strings; emoji fine; avoid `;` (CSV export delimiter).
7. Cloudflare fronts the site and the operator watches load. Keep ≤1 req/s,
   single connection, descriptive User-Agent, exponential backoff on 429/5xx.
   TOS prohibits data harvesting — we only touch our own cubes.
8. Stability ranking (most → least): mycubes > commit envelope > cubeJSON
   fields (never row order) > CSV columns (append-only so far).
9. Bulk read-only research data: `aws s3 sync s3://cubecobra-public/export/
   --no-sign-request` (~quarterly refresh) — not for live management.
