# Frappe Skills

A collection of agent skills for building [Frappe Framework](https://frappeframework.com/) applications, plus general code-style and UI design skills.

## Skills

| Skill            | What it covers                                                                                                                                                                                 |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `frappe-app-dev` | Full-stack Frappe: DocTypes, controllers, APIs, database/ORM, hooks, permissions, jobs, realtime, caching, testing, app setup, frontend (Desk/Vue/portal), and the bench CLI + site management |
| `code-style`     | General code style rules                                                                                                                                                                       |
| `ui-design`      | General UI/UX design principles                                                                                                                                                                |
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

Once installed, each skill activates automatically when you ask your agent about a matching task — creating DocTypes, building a Vue SPA, or running `bench migrate` (`frappe-app-dev`); enforcing code style (`code-style`); UI/UX judgment (`ui-design`); and so on.
