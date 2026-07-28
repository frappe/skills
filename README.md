# Frappe Skills

A collection of agent skills for building [Frappe Framework](https://frappeframework.com/) applications, plus general skills for code style, code review, writing, and UI design.

## Skills

| Skill | What it covers |
| ----- | -------------- |
| `frappe-app-dev` | Full-stack Frappe: DocTypes, controllers, APIs, database/ORM, hooks, permissions, jobs, realtime, caching, testing, app setup, frontend (Desk/Vue/portal), and the bench CLI + site management |
| `quality-code-review` | Review checklist for Frappe applications: correctness, security, performance, concurrency, readability, API design, and testing |
| `code-style` | General code style rules |
| `technical-writing` | Write documentation, READMEs, commits, pull requests, and release notes in Simplified Technical English |
| `ui-design` | General UI/UX design principles |
| `draft-security-advisory` | Write a publication-ready GitHub Security Advisory (GHSA) from a vulnerability report — Impact + Workarounds body, CVSS, CWE, versions, credits. User-invoked only: run `/draft-security-advisory` |

## Install

Install all skills from the repo:

```bash
npx skills add frappe/skills
```

Install a single skill:

```bash
npx skills add frappe/skills --skill frappe-app-dev
```

Install several at once:

```bash
npx skills add frappe/skills \
  --skill frappe-app-dev --skill code-style --skill ui-design
```

Skills are matched by the `name` field in each `SKILL.md` frontmatter, and live under `skills/<name>/`.

## Usage

Most skills activate automatically when you ask your agent about a matching task. Examples: create a DocType, build a Vue SPA, or run `bench migrate` (`frappe-app-dev`), review a diff (`quality-code-review`), write a commit message (`technical-writing`), or lay out a page (`ui-design`).

Some skills only run when you call them. Run `/draft-security-advisory` to start that skill.
