# Security

This document is the trust model for the `last30days` research skill. It
explains what the skill does on your machine, where it sends data, how it
handles credentials, and how to report a security issue — so you can evaluate
it *before* you install or run it, including when an installer's security scan
flags it.

The skill is open source (MIT). Every script it ships lives in this repository
under `skills/last30days/`, so every claim below is verifiable by reading the
code. The agent-facing behavior contract is the "Security & Permissions"
section of `skills/last30days/SKILL.md`; the knob-by-knob reference is
`CONFIGURATION.md`.

## What the skill does

`/last30days` researches what people are saying about a topic across public
sources (Reddit, X, YouTube, TikTok, Hacker News, Polymarket, GitHub, Bluesky,
TruthSocial, Digg, jobs boards, and the web) and writes a cited research
briefing.

Mechanically, it:

- runs a local Python engine (`skills/last30days/scripts/last30days.py`) and,
  for X search, a vendored Node client that is a search-only subset of the MIT
  `@steipete/bird` CLI (`scripts/lib/vendor/bird-search/`);
- makes outbound calls to the platforms being researched, providers you
  configure, local browser-backed services you opt into, and watchlist webhooks
  you configure (see "Network destinations");
- runs local binaries when present: `yt-dlp` (YouTube transcripts), the `gh`
  CLI (GitHub search), `digg-pp-cli` (Digg), and optionally the `xurl` CLI
  (official X API v2, OAuth2). YouTube retrieval can also be routed through a
  configured `ssh` host, and the setup wizard may run `brew install yt-dlp` if
  Homebrew is available and you choose auto-install;
- reads optional credentials from environment variables, `.env` files, the
  macOS Keychain, or `pass` (see "Credentials");
- writes briefings when `--save-dir` is supplied or `LAST30DAYS_MEMORY_DIR` is
  set. The slash-command wrapper supplies `--save-dir` from
  `${LAST30DAYS_MEMORY_DIR:-$HOME/Documents/Last30Days}`; a direct
  `last30days.py` invocation without either setting does not write a briefing
  file. In watchlist mode only, it keeps local state in a SQLite database.

The engine contains no telemetry, analytics, or phone-home code.

## What the skill does not do

- It never posts, likes, replies, or modifies anything on any platform.
- It never accesses your accounts beyond performing searches — it cannot
  publish as you.
- It never shares a key across providers: the OpenAI key only goes to
  `api.openai.com`, the xAI key only to `api.x.ai`, and so on.
- It never logs or writes API keys into report files, and debug output redacts
  request keys (including keys a provider echoes back in an error body).
- It has no hidden telemetry endpoint. Outbound destinations are the hosts in
  "Network destinations," configured provider base URLs, configured local
  services, and configured watchlist delivery webhooks.

## Trust boundary

The skill runs with the same permissions as the agent that invokes it: an
agent running it can read any file and run any program the user account can.
Treat "review before use" as applying to the agent runtime as much as to the
skill. Install through a CLI you trust (`npx skills add
mvanhorn/last30days-skill`), pin the version you reviewed, and avoid running
the skill under accounts that hold credentials you are not willing to expose
to the agent.

## Why installer security scanners flag this skill

The `npx skills` installer runs three independent scanners — Gen Agent Trust
Hub, Socket, and Snyk — and shows their results at install time. Research
aggregators look unusual to supply-chain scanners by design: the skill's core
job is outbound network access, subprocess execution (Python, Node, `yt-dlp`,
`gh`), and optional use of API-key environment variables, all behaviors
scanners conservatively rate as risky. Current results are public at
<https://skills.sh/mvanhorn/last30days-skill> and change as both the skill and
the scanners evolve.

If a scan flags this repository, check the specific finding rather than the
headline risk: the repo's own CI (see "Security posture") runs dependency
audits and SAST on every commit, and the engine's network behavior is the
documented list below, not an open pipe.

## Credentials

Several sources need no credentials at all: Hacker News, Polymarket, public
Reddit, YouTube, GitHub (uses the `gh` CLI's existing auth), and Digg. Optional
keys unlock the remaining sources and are resolved in this priority order:

1. process environment variables;
2. project-scoped `.claude/last30days.env`, then the global
   `~/.config/last30days/.env`;
3. macOS Keychain items prefixed `last30days-`
   (`skills/last30days/scripts/setup-keychain.sh`);
4. a `pass`(1) store (`skills/last30days/scripts/setup-pass.sh`), read by
   `lib/env.py::_load_pass` as the lowest-priority source and decrypted
   transiently so secrets stay encrypted at rest. The source is additive: it is
   skipped silently when `pass` is not installed.

Secret handling checks:

- secret files should be `0600` on POSIX hosts. The engine emits a
  non-blocking warning when group or other users can read a `.env` file, then
  continues loading it (`lib/env.py`, `_check_file_permissions`);
- keys stay with their provider and are never written into output files;
- `--diagnose` reports which sources are *available*, not the keys themselves.

The source-by-source key table lives in `CONFIGURATION.md`.

### Browser-cookie authentication for X

When no explicit X credential is configured, the engine by default probes
Firefox and Safari cookie stores for X session cookies, reading local files
silently. Chromium-family browsers are only probed when you opt in, because
their cookie stores require a macOS Keychain prompt. Control this explicitly:

```bash
FROM_BROWSER=off      # never touch browser cookie stores (recommended for strict setups)
FROM_BROWSER=firefox  # only a specific browser
FROM_BROWSER=auto     # also try Chromium-family browsers (may prompt for Keychain access)
```

Cookie reads stay on your machine — extracted cookies are sent only to X
endpoints for the search being run. If you prefer zero ambient access, set
`FROM_BROWSER=off` and provide `XAI_API_KEY` or another explicit X credential
instead.

## Network destinations

Outbound calls go to the platforms being researched, the providers and base
URLs you configure, local browser-backed services you opt into, and watchlist
delivery webhooks you configure. Grouped by purpose:

| Purpose | Hosts |
|---|---|
| X / Twitter search | `api.x.com` (official API v2), `x.com`, `twitter.com`, `upload.twitter.com` (cookie auth), `api.x.ai` (xAI), `xquik.com`, `api.scrapecreators.com` |
| Reddit | `reddit.com`, `www.reddit.com` (public data; ScrapeCreators only as a backup) |
| YouTube / TikTok / Instagram / Threads / Pinterest | `www.youtube.com` (via local `yt-dlp`; optionally over a configured `ssh` host), `www.tiktok.com`, `www.instagram.com`, `www.threads.net`, `www.pinterest.com`, `api.scrapecreators.com` |
| Hacker News | `hn.algolia.com`, `news.ycombinator.com` |
| Polymarket | `polymarket.com`, `gamma-api.polymarket.com` |
| GitHub | `github.com`, `api.github.com` (via `gh`) |
| Bluesky | `bsky.social` for session creation/refresh, `api.bsky.app` for search by default, or a configured `BSKY_SEARCH_HOST` override |
| TruthSocial / Digg | `truthsocial.com`, `di.gg` |
| Xiaohongshu / RED | local HTTP service `http://localhost:18060`, Docker-host fallback `http://host.docker.internal:18060`, or the configured `XIAOHONGSHU_API_BASE`; result links point at `www.xiaohongshu.com` |
| Web search & grounding | `api.openai.com`, `openrouter.ai`, `api.x.ai`, `generativelanguage.googleapis.com`, `r.jina.ai`, `html.duckduckgo.com`, plus Brave/Parallel/Exa/Serper APIs when configured |
| Jobs / hiring signals | `boards.greenhouse.io`, `apply.workable.com`, `jobs.smartrecruiters.com` |
| Reasoning provider | `api.openai.com`, `chatgpt.com/backend-api` (Codex login), `api.x.ai`, `openrouter.ai`, `generativelanguage.googleapis.com` |
| Watchlist delivery | the configured Slack incoming webhook or generic HTTPS webhook URL (`skills/last30days/scripts/watchlist.py` rejects non-HTTPS delivery URLs) |

## Security posture

The repository separates blocking PR checks from scheduled/advisory posture
checks:

- blocking checks on pull requests and pushes to `main`: the full test suite,
  the `uv audit --locked` dependency audit, the verified-secret scan
  (TruffleHog, `--results=verified`), and zizmor for GitHub Actions hardening.
  Dependency review additionally runs on pull requests only;
- advisory: the Semgrep SAST scan runs on pull requests and pushes to `main`
  with `continue-on-error`, so source-level findings are visible while the
  baseline is cleaned up;
- OpenSSF Scorecard runs on the default branch and on a weekly scheduled workflow;
  it publishes SARIF/trend data and does not block pull-request merges;
- OSV-Scanner runs on a weekly scheduled workflow to catch newly disclosed CVEs in
  lockfiles between PRs; it is currently advisory (`fail-on-vuln: false`).

The test suite contains security-boundary tests (e.g. credential-source
precedence, secret-file permission warnings, and setup-store key masking).

## Reporting a vulnerability

The repository accepts private vulnerability reports through GitHub (Settings
→ Security → "Report a vulnerability" on the repo page). Please include:

- the affected version (plugin version and install method);
- a minimal reproduction and the platform it applies to;
- the impact as concretely as you can.

Scanner findings (Gen/Socket/Snyk) are usually not vulnerabilities — if a
scanner flags a specific dependency or behavior, open a regular issue with the
scanner name, the finding, and the scanned version, and the maintainers will
triage it. Do not post details of a confirmed exploit publicly before it is
addressed.
