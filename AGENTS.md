# AGENTS.md

## Before implementing

Read `coding-guide.md` and the [README](README.md) before changing code.

## Documentation upkeep

After every code implementation, review and update `README.md` before finishing:

- keep the project summary, current status, and next steps accurate;
- keep links to the v0.1 spec, ADRs, tickets, and guides current;
- update `docs/guide.md` when user-facing behavior or examples change;
- update `coding-guide.md` when setup, architecture, conventions, or testing change.

Add or amend an ADR for significant architectural decisions, and update `GLOSSARY.md` when domain vocabulary changes.

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues in `szerming/sphinx-prefect`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `GLOSSARY.md` + `docs/adr/`. See `docs/agents/domain.md`.

## Planning docs

- v0.1 spec: `docs/specs/0001-sphinx-prefect-v0.1.md`
- Decisions: `docs/adr/`
- Tickets: `docs/tickets/` (published as GitHub #1–#10)
- Glossary: `GLOSSARY.md`
