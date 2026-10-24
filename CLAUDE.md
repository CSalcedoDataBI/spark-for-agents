# Agent instructions

This repository is **public and in pre-release**. Write every issue and commit with that in mind:
no client names, no real engagements, no credentials, and nothing from private repositories.

Its direction is set by [FICHA.md](FICHA.md), and the
`experto` agent (`.claude/agents/experto.md`) merges against it.

## Rules specific to this repo

- **Never add a function name to anything an agent reads unless it came from an engine export**
  (`SHOW FUNCTIONS` / `DESCRIBE FUNCTION EXTENDED`, or introspection of `pyspark`). This library
  exists to stop invention, so it cannot contain any.
- **Generated cards are written only by the export script.** Never edit one by hand; write a note
  instead.
- **Every number in the README is counted from the tree**, not typed. Until a check backs a
  number, do not write it.
- **CI runs on GitHub runners, never on a self-hosted one.** The repo is public, and a self-hosted
  runner would execute fork PRs on the maintainer's machine.
- The repository is in English. Specs and ADRs under `docs/` are in Spanish, as in dax-for-agents.
