---
name: deck-continue
description: Resume the most recent deck workflow from where it left off. No arguments needed — reads session state automatically.
---

HARD RULES — NEVER VIOLATE:
1. Do NOT generate or invent campaign names. Read them from the template config JSON.
2. Do NOT make tool calls not listed in these instructions.
3. Do NOT write to formula cells under any circumstances.
4. Do NOT skip gates — wait for user confirmation at every gate.
5. Do NOT open files you are about to write to programmatically. Keep them closed during writes.
6. Do NOT add features, steps, or checks not specified here.
7. Do NOT proceed past a failed step — stop and report the failure.
8. If a tool call fails, report the error. Do NOT retry more than once.
9. Keep all client-specific data in the client folder under 4. Reports/. Never write client data to .claude/data/.
10. Use HAIKU for research agents unless explicitly told otherwise.
11. All Attio, Slack, and other MCP tools are READ-ONLY. Never use create, update, or delete MCP actions.

---

You are the `deck-continue` command — a resume dispatcher. Read session state, determine the next phase, and hand off to the correct skill.

## Step 1: Find Session State

```bash
WS="$(printf '%s' "${JOLLY_WORKSPACE:-.}" | tr -d '\r')"
ls "$WS/.claude/data/session_state_"*.md 2>/dev/null | sort | tail -1
```

If no session state files exist:

```
No active session found. Start a new one with:

  /deck-auto [Company Name]
```

Then stop.

If multiple session files exist for different companies, read each one and present a numbered list:

```
Active sessions:

  [1] [Company A] — Phase 2 complete, next: /deck-model
  [2] [Company B] — Phase 4 complete, next: /deck-qa

→ Number to continue, or company name
```

Wait for selection.

## Step 2: Read Session State

Read the selected session state file. Extract:
- `company_name` (from `## Company`)
- `client_root` (from `## Client Root`)
- Phase checklist (from `## Phase Checklist` — which phases are `complete` vs `pending`)
- Next action (from `## Next Action`)

Show the user:

```
Resuming: [COMPANY_NAME]

  Phase 1: Start          ✓
  Phase 2: Research        ✓
  Phase 3: Model           ✓
  Phase 4: Format          ○ ← next
  Phase 5: QA              ○

→ "go" to continue with Phase [N], or "phase [N]" to jump to a specific phase
```

Wait for input. Accept:
- `go` — run the next pending phase
- `phase 1` through `phase 5` — jump to that specific phase
- `restart` — start over from Phase 1

## Step 3: Dispatch to Phase

Based on the user's choice, run the corresponding skill **in full** as if the user had invoked it directly. Follow every step, gate, and instruction in the target skill exactly.

| Next Phase | Skill to Run | What It Does |
|---|---|---|
| Phase 1 | `/deck-start [COMPANY_NAME]` | Init folders, copy templates, detect branch |
| Phase 2 | `/deck-research` | Research agents, campaign selection |
| Phase 3 | `/deck-model` | Populate Excel model |
| Phase 4 | `/deck-format` | Banners, text, brand assets, vF, PDF |
| Phase 5 | `/deck-qa` | 11 quality checks |

Read the full SKILL.md for the target phase and execute it from the beginning. The session state provides all the context the skill needs (company name, paths, vertical, branch, context).

**Do not summarize or skip steps.** Run the skill as written, including all gates.

## Edge Cases

**All phases complete:**
```
All 5 phases complete for [COMPANY_NAME]. Deck is ready for delivery.

Files:
  vF:    [vf path]
  Model: [model path]
  PDF:   [pdf path]

Nothing left to do. To re-run QA: type "phase 5".
```

**Phase 3 selected but Phase 2 not complete:**
```
Phase 2 (Research) must complete before Phase 3 (Model).
Run Phase 2 first, or type "phase 2" to start it.
```

Phases must run in order: 1 → 2 → 3 → 4 → 5. Do not allow skipping ahead (except re-running a completed phase).
