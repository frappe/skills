# Payloads for file, path and URL fixes

Use only the rows for the sink you fixed. The "refused" column is the **probes** set and the
"allowed" column is the **allowed calls** set of [verify.md](../../verify.md). Each allowed call
must give the same result before and after the fix.

| Sink | Refused after the fix | Allowed before and after |
|---|---|---|
| SSRF | `http://127.0.0.1:<port>/`, `http://169.254.169.254/latest/meta-data/`, `http://[::1]/`, `http://2130706433/`, `http://0x7f000001/`, `http://100.64.0.1/` (shared space: neither private nor global), a public host that 302-redirects to `127.0.0.1`, a DNS name resolving to loopback, `file:///etc/passwd`, `gopher://` | a public `https://` URL the feature is meant to fetch |
| SSRF through PDF | `<img src="http://<listener>/">`, `<iframe src="file:///etc/passwd">`, `<meta name="pdfkit-enable-local-file-access" content="">` | a print format whose images come from the site's own `/files/` |
| Traversal | `../../site_config.json`, `..%2f..%2fsite_config.json`, `%2e%2e/`, absolute `/etc/passwd`, `files_evil/x` (sibling prefix), a symlink inside `public/files` pointing outside | a file name the feature itself wrote under the base directory |
| `file_url` | another user's `/private/files/x.csv`, a non-CSV file named `.csv` | a public file, a file attached to two documents where the caller can read only one |
| Upload | `.svg` containing `<script>`, `.html`, `image/svg+xml` as Guest, attaching to a document the caller cannot write, attaching a File the caller cannot read | a `.png` or `.pdf` attached by a user with `write` on the document |
| XXE | `<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>`, an external DTD on your listener, billion laughs | a valid document of the shape the importer expects |
| Redirect | the table below, plus `Host: evil.com` and `X-Forwarded-Host: evil.com` on a magic-link or reset request — read the URL that was emailed | a relative path on the site, such as `/app/todo` |
| CSV | export a value `=HYPERLINK("http://x")` and open it in a spreadsheet: it shows as text | re-import that export: the value comes back with no stray `'` |
| Archive | a 10 KB zip that expands to 1 GB, a member named `../../x`, a member whose declared size is smaller than its real size | a small zip of ordinary files |

## Redirect checks that look right and are not

Measured by running both generations of frappe's `sanitize_redirect` on each input:

| Input | "No netloc → allow" check | "Rebuild on own host" check |
|---|---|---|
| `//evil.com/x` | refused | `https://site/app` |
| `/\evil.com` | **passed** — browsers read it as `//evil.com` | `https://site/\evil.com` |
| `https:evil.com` | **passed** | `https://site/evil.com` |
| `javascript:alert(1)` | **passed** | `https://site/alert(1)` |
| `https://site@evil.com/` | refused | `https://site/app` |

Rebuild the URL on your own host. Do not test whether it is relative.
