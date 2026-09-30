---
id: A12
area: customization
---
# A12 — Pin nothing the framework owns. Branch per framework major

**Why:** An app that pins its own version of a package the framework also uses takes the site
down at the next framework upgrade. An app with one branch cannot support two framework majors,
so an upgrade of the bench breaks the app for every site at once.

## Bad

```toml
# pyproject.toml
[project]
name = "my_app"
dependencies = [
    "pymysql==1.0.2",
    "redis==3.5.3",
    "requests",
]
```

## Good

```toml
# pyproject.toml
[project]
name = "my_app"
dependencies = [
    "xmlsec>=1.3.13,<2",
]
```

```
# branches
develop        tracks frappe develop
version-16     tracks frappe version-16
version-15     tracks frappe version-15
```

## Find

- `rg -n '^(frappe|erpnext|pymysql|redis|jinja2|werkzeug|requests|cryptography|pypika|rq|click)' pyproject.toml requirements.txt`.
- Any `==` pin in the app on a package that also appears in the framework's `pyproject.toml`.
- `git branch -r` on the app. Only `main` or `master` is a finding when the app depends on
  frappe or erpnext.
- `rg -n 'import (\w+)' --type py` for a package that appears in no dependency list.

## Confirm

Compare the app's dependency names against
`<bench>/apps/frappe/pyproject.toml`. A shared name with a pin in the app is a
finding, whatever the version.

A pin on a package the framework does not declare is correct, and an upper bound on a major
version is good practice.

The framework drops unused dependencies at major versions. An app that imports a package
because "frappe already installs it" and declares nothing is the same finding from the other
side, and A13 covers it.

An app with one branch is a finding only when it claims support for more than one framework
major, or when its users run more than one.
