---
id: B44
area: correctness
semgrep: {rules: [frappe-breaks-multitenancy, frappe-overriding-local-proxies], coverage: partial}
---
# B44 — Do not keep site or request state at module or class scope

**Why:** A worker process serves many sites and many requests. A module-level variable is
created once, at import, when there may be no site at all, and it is then shared by every
request that process handles. A value read from one site's database is served to the next site.
A cache written into a class attribute never expires. The failure is intermittent and looks
like a data leak between tenants.

## Bad

```python
# my_app/pricing.py
DEFAULT_CURRENCY = frappe.db.get_single_value("Global Defaults", "default_currency")

class PriceEngine:
    rate_cache = {}          # shared by every site in this process

    def get_rate(self, item):
        if item not in self.rate_cache:
            self.rate_cache[item] = frappe.db.get_value("Item Price", item, "price_list_rate")
        return self.rate_cache[item]
```

## Good

```python
# my_app/pricing.py
from frappe.utils.caching import request_cache

@request_cache
def get_default_currency():
    return frappe.db.get_single_value("Global Defaults", "default_currency")

class PriceEngine:
    def __init__(self):
        self.rate_cache = {}

    def get_rate(self, item):
        if item not in self.rate_cache:
            self.rate_cache[item] = frappe.db.get_value("Item Price", item, "price_list_rate")
        return self.rate_cache[item]
```

## Find

- `rg -n '^[A-Z_]+\s*=\s*frappe\.' --type py` and `rg -n '^\w+\s*=\s*frappe\.(db|get_all|get_doc|get_meta|get_hooks|conf|local|flags)' --type py`.
- `rg -n '^\s{4}\w+\s*=\s*(\{\}|\[\])' --type py` inside a class body, where the attribute is
  written later.
- `rg -n 'frappe\.(db|qb|conf|flags|session|local|form_dict)\s*=' --type py`. Assigning to a
  framework proxy replaces it for the whole process.
- `rg -n 'global \w+' --type py` in the app.

## Confirm

A constant, a compiled regular expression, a function and a class at module scope are correct.
The finding is a value that depends on a site, a user, a request or the database. `frappe.local`
holds request-scoped state and is reset per request, so it is the right place for a per-request
value; the framework caching decorators (`request_cache`, `site_cache`, `redis_cache`) are the
right place for a cached one. `site_cache` keeps its result in every worker process, so it
multiplies memory; that cost belongs to the performance rules.
