export const meta = {
	name: 'deep-app-audit',
	description: 'Audit a Frappe app for security, correctness, and customization defects: scan with every prompt, verify each candidate in a fresh context, then compile one report',
	whenToUse: 'A full or partial deep audit of a Frappe app checkout, driven by the security scopes and the quality rules of the deep-app-audit skill.',
	phases: [
		{ title: 'Inventory', detail: 'resolve paths, list the prompts, and build the static entry-point inventory' },
		{ title: 'Site', detail: 'create a disposable test site, install the app, add one user per actor' },
		{ title: 'Scan', detail: 'one agent per security scope and per quality rule, finding candidates' },
		{ title: 'Verify', detail: 'one agent per candidate, in a fresh context, trying to refute it' },
		{ title: 'Check', detail: 'one agent per whole-surface check, reporting a table rather than findings' },
		{ title: 'Report', detail: 'persist the raw results, then compile one report' },
	],
}

// ---------------------------------------------------------------------------
// Inputs, passed as the `args` object. Only `skillDir` is required.
//   skillDir  the deep-app-audit skill directory           required
//   target    app checkout to audit                        default: current directory
//   output    report path                                  default: <target>/../<app>-deep-audit.md
//   only      id prefixes to run, e.g. ["S-A", "Q-B05"]    default: everything
//   skip      id prefixes to leave out, e.g. ["S-L"]       default: nothing
//   noChecks  skip every whole-surface check               default: false
//   maxCandidatesPerScope  verification cap per prompt     default: 15
//   maxVerifications       verification cap for the run    default: 600
//
// Ids carry a track prefix, so the two prompt sets cannot collide:
//   S-A01 .. S-L02   security scopes          S-P01 .. S-P05   security posture checks
//   Q-A01 ..         customization rules      Q-B01 ..         correctness rules
//   Q-K01 ..         customization checks
//
//   Live test site (optional; the audit degrades to static reading without one):
//   bench           bench directory                        default: found above the checkout
//   site            existing disposable site to reuse      default: create one
//   siteName        name for the created site              default: <app>-audit.localhost
//   dbRootPassword  database root password for new-site    default: none, creation may fail
//   sitePort        port for `bench serve`                 default: 8199
//   noSite          skip the site phase entirely           default: false
//   dropSite        drop the created site when done        default: false, it is kept for triage
// ---------------------------------------------------------------------------

const opts = args || {}
if (!opts.skillDir) return { error: 'args.skillDir is required: the directory that holds this workflow' }

const SKILL = opts.skillDir.replace(/\/+$/, '')
const SEC = `${SKILL}/security`
const QUAL = `${SKILL}/quality`
const TARGET = opts.target || '.'
const ONLY = opts.only || null
const SKIP = opts.skip || []
const MAX_CANDIDATES = opts.maxCandidatesPerScope || 15
const MAX_VERIFICATIONS = opts.maxVerifications || 600
const SITE_PORT = opts.sitePort || 8199
const ADMIN_PASSWORD = 'audit-admin-pw'

const TRACK_NAME = { security: 'Security', correctness: 'Correctness', customization: 'Customization' }
const RANK = { Critical: 0, High: 1, Moderate: 2, Low: 3 }
const bySeverity = (a, b) => (RANK[a.severity] ?? 9) - (RANK[b.severity] ?? 9)

const NO_FIXES = `Never propose a fix, a patch, a remediation, or a "recommended fix". This audit
reports what is wrong and what it affects. Deciding what to change is the maintainer's call,
and a wrong suggestion costs more than a missing one.`

// --- Schemas ----------------------------------------------------------------

const PROMPT_LIST = {
	type: 'array',
	items: {
		type: 'object',
		required: ['id', 'file'],
		properties: {
			id: { type: 'string', description: 'the filename prefix, e.g. A01 from A01-whitelist-authorization.md' },
			file: { type: 'string', description: 'path relative to its prompt directory, e.g. A-authorization/A01-whitelist-authorization.md' },
			title: { type: 'string', description: 'the first heading of the file' },
		},
	},
}

const SETUP_SCHEMA = {
	type: 'object',
	required: ['targetDir', 'securityScopes', 'securityChecks', 'qualityRules', 'qualityChecks'],
	properties: {
		targetDir: { type: 'string', description: 'absolute path of the app checkout under audit' },
		appName: { type: 'string', description: 'the app package name, from the directory holding hooks.py' },
		commit: { type: ['string', 'null'], description: 'short commit hash of the checkout, or null if it is not a git repository' },
		benchDir: { type: ['string', 'null'], description: 'absolute path of the bench that holds the checkout, or null' },
		frameworkVersion: { type: ['string', 'null'], description: 'the Frappe version on that bench, from apps/frappe' },
		dependencies: {
			type: 'array',
			description: 'the apps the target requires or imports, with the path of their checkout on the bench when one exists',
			items: {
				type: 'object',
				required: ['app'],
				properties: { app: { type: 'string' }, path: { type: ['string', 'null'] }, version: { type: ['string', 'null'] } },
			},
		},
		inventoryPath: { type: ['string', 'null'], description: 'absolute path of the inventory JSON, or null if it could not be built' },
		inventoryError: { type: ['string', 'null'], description: 'why the inventory could not be built, if it could not' },
		inventorySummary: { type: ['string', 'null'], description: 'the summary the script printed, verbatim' },
		securityScopes: { ...PROMPT_LIST, description: 'every *.md under the security area directories' },
		securityChecks: { ...PROMPT_LIST, description: 'every *.md under security/checks' },
		qualityRules: { ...PROMPT_LIST, description: 'every *.md under quality/A-customization and quality/B-correctness' },
		qualityChecks: { ...PROMPT_LIST, description: 'every *.md under quality/checks' },
	},
}

const SITE_SCHEMA = {
	type: 'object',
	required: ['ready'],
	properties: {
		ready: { type: 'boolean', description: 'true only when the site answers an HTTP request and the app is in its installed app list' },
		benchDir: { type: ['string', 'null'], description: 'absolute path of the bench directory' },
		site: { type: ['string', 'null'], description: 'the site name' },
		baseUrl: { type: ['string', 'null'], description: 'the base URL that answers, e.g. http://localhost:8199' },
		created: { type: 'boolean', description: 'true when this run created the site, false when it reused one' },
		installedApps: { type: 'array', items: { type: 'string' } },
		users: {
			type: 'array',
			description: 'the test users created, one per actor level',
			items: {
				type: 'object',
				required: ['email', 'password', 'actor'],
				properties: {
					email: { type: 'string' },
					password: { type: 'string' },
					actor: { type: 'string', description: 'Website User, plain System User, or System Manager' },
					roles: { type: 'array', items: { type: 'string' } },
				},
			},
		},
		serveCommand: { type: ['string', 'null'], description: 'the command left running to serve the site, if any' },
		error: { type: ['string', 'null'], description: 'what stopped the site coming up, when ready is false' },
		notes: { type: ['string', 'null'], description: 'anything an auditing agent must know: fixtures loaded, ports, quirks' },
		config: {
			type: 'array',
			description: 'every security-relevant setting found in the bench and site config, whatever its value. A setting that weakens a control changes what an executed proof means, so it must be recorded before any request is sent.',
			items: {
				type: 'object',
				required: ['key', 'value', 'weakens'],
				properties: {
					key: { type: 'string', description: 'the config key, e.g. ignore_csrf, developer_mode, allow_tests' },
					value: { type: 'string', description: 'its value on this site, as written' },
					source: { type: 'string', description: 'common_site_config.json or the site config' },
					weakens: { type: 'boolean', description: 'true when this value disables or loosens a control a finding might otherwise have to defeat' },
					effect: { type: 'string', description: 'one line: which control it weakens and what a verifier must therefore not conclude' },
				},
			},
		},
	},
}

const SEVERITY = { type: 'string', enum: ['Critical', 'High', 'Moderate', 'Low'] }

const SEC_CANDIDATE = {
	title: { type: 'string', description: 'one line, no severity prefix' },
	severity: SEVERITY,
	file: { type: 'string', description: 'path:line, relative to the app checkout' },
	actor: { type: 'string', description: 'Guest, Website User, plain System User, or a named low-privilege role' },
	input: { type: 'string', description: 'the request-controlled value and how it reaches the sink' },
	impact: { type: 'string', description: 'what the actor reads, writes, or executes that they should not' },
	proof: { type: 'string', description: 'the call chain, 1-3 lines' },
}
const SEC_REQUIRED = ['title', 'severity', 'file', 'actor', 'input', 'impact', 'proof']

const QUAL_CANDIDATE = {
	title: { type: 'string', description: 'one line, no severity prefix' },
	severity: SEVERITY,
	file: { type: 'string', description: 'path:line, relative to the app checkout; list other locations in proof' },
	trigger: { type: 'string', description: 'the normal use, data, or sequence of events that starts the failure' },
	failure: { type: 'string', description: 'what goes wrong' },
	impact: { type: 'string', description: 'who carries the failure, and how much' },
	proof: { type: 'string', description: 'the code path, 1-3 lines' },
}
const QUAL_REQUIRED = ['title', 'severity', 'file', 'trigger', 'failure', 'impact', 'proof']

const scanSchema = (props, required) => ({
	type: 'object',
	required: ['candidates', 'coverage'],
	properties: {
		candidates: { type: 'array', items: { type: 'object', required, properties: props } },
		coverage: { type: 'string', description: 'what you searched, what you skipped, what you could not resolve' },
	},
})

const VERDICT_SCHEMA = {
	type: 'object',
	required: ['verdict', 'reasoning'],
	properties: {
		verdict: {
			type: 'string',
			enum: ['confirmed', 'rejected', 'uncertain'],
			description: 'confirmed only when you can state every part of the finding bar yourself',
		},
		severity: { ...SEVERITY, description: 'your own reading of the ladder, not the reported one' },
		reasoning: { type: 'string', description: 'why it stands or falls, citing the code you read' },
		reachability: { type: 'string', description: 'security: the path from an HTTP request to the sink, or why there is none' },
		exploit: { type: 'string', description: 'security: the concrete request an attacker sends, or why it cannot be written' },
		tested: { type: 'boolean', description: 'true only when you executed the proof against the live test site' },
		evidence: { type: 'string', description: 'what you ran against the test site and what came back, when you tested it live' },
		envDependent: { type: 'boolean', description: 'true when the proof depends on a site setting that weakens a control, so the same result may not occur on a normally configured site' },
		envCaveat: { type: 'string', description: 'which setting the proof leaned on, what it means the result does not show, and what would have to be re-tested without it' },
		corrections: { type: 'string', description: 'anything the candidate got wrong' },
		title: { type: 'string', description: 'corrected one-line title, if the reported one is wrong' },
		file: { type: 'string', description: 'corrected path:line, if the reported one is wrong' },
		actor: { type: 'string' },
		input: { type: 'string' },
		trigger: { type: 'string' },
		failure: { type: 'string' },
		impact: { type: 'string' },
		proof: { type: 'string' },
	},
}

const CHECK_SCHEMA = {
	type: 'object',
	required: ['status', 'summary', 'table'],
	properties: {
		status: {
			type: 'string',
			enum: ['pass', 'gaps', 'fail', 'not applicable'],
			description: 'not applicable when the check needs a target this run does not have',
		},
		summary: { type: 'string', description: 'two or three lines: what the posture is today' },
		table: { type: 'string', description: 'the table the Output section of the check asks for, as markdown' },
		gaps: { type: 'array', items: { type: 'string' }, description: 'one line per gap, most consequential first' },
		findings: {
			type: 'array',
			description: 'only what clears the finding bar of the conventions; usually empty. These are NOT verified, so state them conservatively',
			items: {
				type: 'object',
				required: ['title', 'severity', 'file', 'impact', 'proof', 'belongsTo'],
				properties: {
					...SEC_CANDIDATE,
					...QUAL_CANDIDATE,
					belongsTo: { type: 'string', description: 'the scope or rule id this belongs to, e.g. A04 or B05' },
				},
			},
		},
		notes: { type: 'string', description: 'what you could not reach, and why' },
	},
}

// --- Inventory --------------------------------------------------------------

phase('Inventory')

const setup = await agent(`Prepare a deep audit of a Frappe app. Do not audit anything yourself.

1. Resolve the app checkout \`${TARGET}\` to an absolute path and confirm it exists. It is a
   Frappe app: one package inside it holds \`hooks.py\`. Report that package name as \`appName\`.
   Report the short commit hash with \`git -C <targetDir> rev-parse --short HEAD\`, or null.

2. Find the bench, read-only. ${opts.bench ? `It is \`${opts.bench}\`.` : 'A bench directory holds `sites/`, `apps/`, and `Procfile`. Look at the ancestors of the checkout first: an installed app usually sits at `<bench>/apps/<app>`.'}
   If you find one, report the Frappe version from \`apps/frappe/frappe/__init__.py\`. List the
   apps the target requires (\`required_apps\` in \`hooks.py\`, \`pyproject.toml\`) or imports,
   with the absolute path of each on the bench, or null when the bench does not have it.
   Change nothing on the bench.

3. Build the static entry-point inventory. Write it next to the app checkout, not inside it:

   \`python ${SEC}/build_inventory.py <targetDir>/../<appName>-inventory.json --root <targetDir>\`

   If that path is not writable, write to a temporary directory instead. The script is
   read-only, needs no bench, no site, and no database. Report the absolute path it wrote and
   the summary it printed. If it fails, report \`inventoryPath: null\` and the error in
   \`inventoryError\`. The audit still runs without it.

4. List the prompts. The id of a prompt is its filename prefix: \`A01\` from
   \`A01-whitelist-authorization.md\`. Paths are relative to the directory named here.
   - \`securityScopes\`: each \`*.md\` in the area directories of \`${SEC}\`
     (\`A-authorization\` to \`L-supply-chain\`).
   - \`securityChecks\`: each \`*.md\` in \`${SEC}/checks\`.
   - \`qualityRules\`: each \`*.md\` in \`${QUAL}/A-customization\` and \`${QUAL}/B-correctness\`.
   - \`qualityChecks\`: each \`*.md\` in \`${QUAL}/checks\`.
   Do not list files whose name starts with \`_\`, and do not list \`${QUAL}/mechanisms\`.

Change no file inside the app checkout.`, { label: 'setup', schema: SETUP_SCHEMA })

if (!setup) return { error: 'setup agent failed; nothing to audit' }

const track = id => (id.startsWith('S-') ? 'security' : id.startsWith('Q-A') || id.startsWith('Q-K') ? 'customization' : 'correctness')
const tag = (list, prefix, kind, dir) => (list || []).map(p => ({
	id: `${prefix}${p.id}`, bare: p.id, kind, dir, file: p.file, title: p.title || p.id, track: track(`${prefix}${p.id}`),
}))
const selected = t => (!ONLY || ONLY.some(p => t.id.startsWith(p))) && !SKIP.some(p => t.id.startsWith(p))
const byId = (a, b) => (a.id < b.id ? -1 : 1)

const scopes = [
	...tag(setup.securityScopes, 'S-', 'scope', SEC),
	...tag(setup.qualityRules, 'Q-', 'rule', QUAL),
].filter(selected).sort(byId)

const checks = opts.noChecks ? [] : [
	...tag(setup.securityChecks, 'S-', 'check', SEC),
	...tag(setup.qualityChecks, 'Q-', 'check', QUAL),
].filter(selected).sort(byId)

if (!scopes.length && !checks.length) return { error: 'no prompts matched the filter', setup }

const INV = setup.inventoryPath
	? `A static entry-point inventory of this app is at \`${setup.inventoryPath}\`. Read it with
\`jq\`. It is large, so query it, do not cat it. Its \`views\` object holds pre-computed lists
(\`guest_no_permission_check\`, \`sql_direct\`, \`untyped_params\`, and others) and every entry
point carries its file, line, decorators, parameters, permission checks, and reachable sinks.
Use it to enumerate candidates, then read the real code before you report anything: the
inventory is a static approximation and its permission flags are presence checks, not proof.`
	: `No entry-point inventory is available (${setup.inventoryError || 'not built'}). Enumerate
candidates with \`rg\` instead.`

const DEPS = setup.benchDir
	? `The app sits on the bench \`${setup.benchDir}\`, with Frappe ${setup.frameworkVersion || '(version unknown)'}.
The framework and the apps the target needs are there, read-only:
${(setup.dependencies || []).map(d => `- \`${d.app}\`: ${d.path ? `\`${d.path}\`` : 'not on this bench'}${d.version ? ` (${d.version})` : ''}`).join('\n') || '- none found'}
Read their source when a verdict depends on what core does. Change nothing in them.`
	: 'No bench was found, so the framework source is not available locally. Say so when a verdict depends on it.'

// --- Live test site ---------------------------------------------------------

let site = null

if (!opts.noSite) {
	phase('Site')

	const SITE_NAME = opts.siteName || `${(setup.appName || 'app').replace(/_/g, '-')}-audit.localhost`
	const BENCH = opts.bench || setup.benchDir

	site = await agent(`Stand up a disposable Frappe site for an audit, and install the app under audit on it.
Do not audit anything yourself. Later agents send real requests to this site to prove or refute findings.

App checkout: \`${setup.targetDir}\` (app name: \`${setup.appName || 'unknown'}\`). Treat it as
read-only: change no file inside it, and do not \`git checkout\`, stash, or reset it.

1. Find the bench. ${BENCH ? `Use \`${BENCH}\`.` : 'A bench directory holds `sites/`, `apps/`, and `Procfile`. Look at the ancestors of the checkout first.'}
   Confirm it with \`bench --version\` run from that directory. If there is no bench, stop and
   report \`ready: false\` with the reason. Do not install bench, do not install a database
   server, and do not change the machine's configuration.

2. Get a site.
${opts.site
		? `   Reuse the site \`${opts.site}\`. Confirm it exists in \`sites/\` and that it is not a production
   site: if it carries real data, stop and report \`ready: false\` rather than touching it.`
		: `   Site name: \`${SITE_NAME}\`. If a site with that name already exists, reuse it: this workflow
   owns that name. Otherwise create it:

   \`bench new-site ${SITE_NAME} --admin-password ${ADMIN_PASSWORD} --no-mariadb-socket${opts.dbRootPassword ? ` --db-root-password '${opts.dbRootPassword}'` : ''}\`

   The command must never block on a prompt: pass every password on the command line and add
   \`--force\` only if the name exists but is broken. Common failures are a missing database root
   password, a database server that is not running, and a name that is already taken. If it
   fails, report \`ready: false\` and the exact error. The audit still runs without a site.

   Never create, modify, drop, or migrate any site other than \`${SITE_NAME}\`.`}

3. Install the app and its dependencies: \`bench --site <site> install-app <app>\`. Install the
   apps the checkout's \`hooks.py\` or \`pyproject.toml\` requires first, if any are missing. Then
   record the installed app list from \`bench --site <site> list-apps\`.

4. Create one test user per actor level, so a verifier can act as each. Use
   \`bench --site <site> console\` or \`bench --site <site> execute\`, set \`enabled = 1\` and a known
   password on each, and disable any onboarding or password-reset requirement:
   - \`audit-website@example.com\`: Website User, no other role
   - \`audit-user@example.com\`: plain System User, no other role
   - \`audit-manager@example.com\`: System User plus System Manager, for the "what can they
     already do" comparison
   Give them all the password \`audit-user-pw\`. Report each user with its actual roles.

5. Serve the site on port ${SITE_PORT} in the background, so agents can reach it over HTTP:
   \`bench serve --port ${SITE_PORT}\` (run it in the background from the bench directory). If the
   bench uses a site resolution that needs a Host header, say so in \`notes\`: agents will need
   \`curl -H "Host: <site>"\`.

6. Record the site's security-relevant configuration, in \`config\`. Read
   \`sites/common_site_config.json\` and the site's own \`site_config.json\`, and report every
   key that changes how a control behaves: at least \`ignore_csrf\`, \`developer_mode\`,
   \`allow_tests\`, \`server_script_enabled\`, \`disable_website_cache\`, \`maintenance_mode\`,
   and any \`*_disabled\` or \`allow_*\` key you find. Report each one whatever its value, and
   set \`weakens: true\` where the value disables or loosens a control.

   A bench with \`ignore_csrf: 1\` accepts a cross-site request that production would reject, so
   a verifier who sends one and gets a 200 has proved nothing about production. Every later agent
   is told what you record here. If you cannot read the config, say so in \`notes\`: an unknown
   configuration is not a safe one.

7. Prove the site is usable before you report success. All of these must pass:
   - \`curl -sS -o /dev/null -w '%{http_code}' <baseUrl>/api/method/ping\` returns 200
   - a login as \`audit-user@example.com\` through \`/api/method/login\` returns 200 and sets a cookie
   - the app appears in \`list-apps\`
   Only then report \`ready: true\`. If any check fails, report \`ready: false\` with the failure:
   a site that half works is worse than no site, because verifiers will read its errors as evidence.

Report the bench directory, the site name, the base URL, the users with their passwords, and
anything an auditing agent must know to use it.`, { label: 'site', schema: SITE_SCHEMA })

	if (site && site.ready) {
		log(`site ${site.site} ready at ${site.baseUrl} (${(site.installedApps || []).join(', ')})`)
	} else {
		log(`no live site: ${(site && site.error) || 'site agent failed'}; the audit continues statically`)
		site = null
	}
}

const WEAKENED = site && Array.isArray(site.config) ? site.config.filter(c => c && c.weakens) : null

if (WEAKENED && WEAKENED.length) {
	log(`site config weakens ${WEAKENED.length} control(s): ${WEAKENED.map(c => `${c.key}=${c.value}`).join(', ')}; findings that depend on these are flagged`)
}

const SITE_FACTS = site
	? `- Site: \`${site.site}\` at \`${site.baseUrl}\`${site.serveCommand ? ` (served by \`${site.serveCommand}\`)` : ''}
- Bench: \`${site.benchDir}\`. \`bench --site ${site.site} console\` and \`bench --site ${site.site} execute\` both work
- Test users, password as given:
${(site.users || []).map(u => `  - \`${u.email}\` / \`${u.password}\`: ${u.actor}${u.roles && u.roles.length ? ` (roles: ${u.roles.join(', ')})` : ''}`).join('\n') || '  - none created'}
- Administrator password: \`${ADMIN_PASSWORD}\`
${site.notes ? `- Notes: ${site.notes}\n` : ''}${WEAKENED && WEAKENED.length ? `
**This site's configuration is not production's.** These settings are set here and each one
disables or loosens a control:
${WEAKENED.map(c => `  - \`${c.key} = ${c.value}\`${c.source ? ` (${c.source})` : ''}: ${c.effect || 'weakens a control'}`).join('\n')}

A result that occurs only because one of these is set has not been proved against a normal
site. When a finding depends on one, say so on the finding itself and set \`envDependent\`.
Do not silently upgrade such a result into a confirmation.
` : ''}
Rules for the site:
- It is disposable. Write to it, break it, escalate on it. Do not touch any other site.
- Prove impact, do not maximise it: read one record you should not read, do not delete the data.
- Do not run a payload that leaves the machine: no reverse shells, no outbound exfiltration.
  For SSRF and outbound scopes, point the payload at a local listener you start yourself.
- A failed attempt is evidence too. Record exactly what came back.`
	: null

const LIVE_SEC = site
	? `A live, disposable test site runs this app. Use it to test what you cannot settle by reading:

${SITE_FACTS}

Log in with \`curl -c jar -X POST <baseUrl>/api/method/login -d 'usr=...&pwd=...'\`, then reuse
\`-b jar\` for the request you are testing. A response you actually received beats any amount of
reasoning about what the code would do.`
	: `No live site is available: this audit is a read of the source. Every claim must come from the
code itself, cited by file and line.`

const LIVE_QUAL = site
	? `A live, disposable test site runs this app. The audit reads code, so do not use the site to
hunt. Use it only to show that a failure you found by reading does occur: run a patch twice,
save a document through the path you traced, or call the hook with \`bench --site ${site.site} execute\`
or \`console\`. A failure you saw beats a failure you reasoned about.

${SITE_FACTS}`
	: `No live site is available: this audit is a read of the source. Every claim must come from the
code itself, cited by file and line.`

log(`${scopes.length} scans (${scopes.filter(s => s.kind === 'scope').length} security scopes, ${scopes.filter(s => s.kind === 'rule').length} quality rules) and ${checks.length} checks over ${setup.appName || setup.targetDir}${setup.inventoryPath ? ' (inventory built)' : ' (no inventory)'}${site ? ', live site' : ''}`)

// --- Prompts ----------------------------------------------------------------

const secScanPrompt = s => `You audit a Frappe app for security defects. Your scope is ${s.bare}, and only ${s.bare}.

1. Read \`${SEC}/_conventions.md\` first. It defines the method, the four-part bar a finding
   must clear, the known non-findings, and the severity ladder. It governs everything below.
2. Read \`${SEC}/${s.file}\`. That is your scope. Audit nothing outside it: another agent has
   every other scope, and overlap wastes both of us.
3. The app checkout is \`${setup.targetDir}\`. Treat it as read-only: change no file in it.

${INV}

${DEPS}

${LIVE_SEC}

Report every candidate that clears the four-part bar: entry point, actor, input, impact. Each
candidate is verified independently afterwards by an agent that reads the code fresh and tries
to refute it, so:
- Do not soften or drop a candidate you believe in. State it plainly and let verification test it.
- Do not pad the list with maybes. An unreachable sink is not a candidate, and a long list of
  weak candidates buries the real ones.
- Cite the real file and line. The verifier reads the code, not your excerpt, and a wrong
  citation reads as a fabricated finding.

${NO_FIXES}

If the scope carries an \`Applies to:\` line and this app does not match it, return an empty
candidate list and say so in \`coverage\`. That is a correct result, not a failure.`

const qualScanPrompt = s => `You audit a Frappe app for ${s.track} defects. Your rule is ${s.bare}, and only ${s.bare}.

1. Read \`${QUAL}/_audit.md\` first. It defines the method, the four-part bar a finding must
   clear, the known non-findings, and the severity ladder. It governs everything below.
2. Read \`${QUAL}/${s.file}\`. That is your rule. Audit nothing outside it: another agent has
   every other rule, and overlap wastes both of us.
3. If the rule's frontmatter names a \`mechanism\`, read that page in \`${QUAL}/mechanisms/\`.
4. The app checkout is \`${setup.targetDir}\`. Treat it as read-only: change no file in it.

${DEPS}

${INV}

${LIVE_QUAL}

Report every candidate that clears the four-part bar: location, trigger, failure, impact. Each
candidate is verified independently afterwards by an agent that reads the code fresh and tries
to refute it, so:
- Do not soften or drop a candidate you believe in. State it plainly and let verification test it.
- Do not pad the list with maybes. A practice the code breaks without a failure is not a
  candidate, and a long list of weak candidates buries the real ones.
- Cite the real file and line. The verifier reads the code, not your excerpt, and a wrong
  citation reads as a fabricated finding.

${NO_FIXES} The rule's \`## Good\` section already shows the accepted practice.

If the rule carries an \`Applies to:\` line and this app does not match it, return an empty
candidate list and say so in \`coverage\`. That is a correct result, not a failure.`

const secVerifyPrompt = (s, c) => `You are the independent verifier for one candidate security finding in a Frappe app.
You did not find it. Another agent did, and it may be wrong. Your job is to try to refute it.

Candidate, as reported:
\`\`\`json
${JSON.stringify(c, null, 1)}
\`\`\`

Context:
- App checkout: \`${setup.targetDir}\`. Read-only, change no file.
- The scope it came from: \`${SEC}/${s.file}\`
- The rules it was judged against: \`${SEC}/_conventions.md\`. Read the "Known non-findings"
  and "Severity" sections; they decide most verdicts.

${DEPS}

${LIVE_SEC}

Work in this order:
1. Read the cited code and enough of what surrounds it to know what really happens. Do not
   trust the quoted excerpt or the quoted line number. Verify both.
2. Reachability. Trace an actual path from an HTTP request to the sink: a whitelisted method,
   a doctype controller method reachable over the API, a portal route, a socketio handler, a
   hook, or a job that consumes user data. If no such path exists, reject.
3. Exploitability. Write the concrete request the stated actor sends, with the parameter values
   that trigger it. If you cannot write that request, reject.${site ? `
   Then send it against the test site as that actor, and record what came back. A 403, a
   \`PermissionError\`, or a validation failure refutes the finding as reported: say which
   control produced it. A 200 that returns the data confirms it. If the request needs a fixture
   the site does not have, create the fixture as Administrator, then send the request as the
   low-privilege actor; a finding that needs Administrator to set up its own preconditions is
   weaker, so say so.` : ''}
4. Controls. Check for a permission check, a validation, a decorator, or a caller-side guard
   that the finder missed, including one several frames up the call chain. A control that
   actually covers this actor and this object rejects the finding.${WEAKENED && WEAKENED.length ? `
4a. Environment. This test site sets ${WEAKENED.map(c => `\`${c.key}=${c.value}\``).join(', ')}, which
   weakens a control. Ask whether your result depends on that. If the request you sent would
   have been refused on a site without it, you have not proved what you think: set
   \`envDependent: true\`, write the \`envCaveat\`, and keep the verdict only for the part that
   stands without the setting.` : ''}
5. Severity. Assign it yourself from the ladder in the conventions. Do not inherit the reported
   severity: finders overstate. The actor decides most of it: what a System Manager can
   already do is not a finding when they do it another way.
6. Correct the record. If the finding is real but the file, line, actor, input, or impact is
   wrong, confirm it and supply the corrected values.

Default to \`rejected\` when you are unsure. Use \`uncertain\` only when the code is genuinely
ambiguous (an unresolvable dynamic dispatch, a hook whose registration you cannot find) and
say exactly what you could not resolve. A confirmed finding that turns out to be wrong costs
the maintainer more than a rejected finding that turns out to be real.

${NO_FIXES}`

const qualVerifyPrompt = (s, c) => `You are the independent verifier for one candidate ${s.track} finding in a Frappe app.
You did not find it. Another agent did, and it may be wrong. Your job is to try to refute it.

Candidate, as reported:
\`\`\`json
${JSON.stringify(c, null, 1)}
\`\`\`

Context:
- App checkout: \`${setup.targetDir}\`. Read-only, change no file.
- The rule it was judged against: \`${QUAL}/${s.file}\`. Its \`## Confirm\` section separates a
  true positive from a false positive.
- The audit conventions: \`${QUAL}/_audit.md\`. Read the "Known non-findings" and "Severity"
  sections; they decide most verdicts.

${DEPS}

${LIVE_QUAL}

Work in this order:
1. Read the cited code and enough of what surrounds it to know what really happens. Do not
   trust the quoted excerpt or the quoted line number. Verify both.
2. Apply the rule's \`## Confirm\` section to this code. If the code passes it, reject.
3. Trigger. Decide whether the stated trigger occurs in the use of this app: a real call path,
   a hook that is registered, a patch that is listed, a condition that a normal site can meet.
   Dead code, or a trigger that no user or job can cause, rejects the finding.
4. Failure. Read the framework source where the failure depends on what core does, and decide
   whether the failure really occurs. A guard in a caller, in the framework, or in the schema
   (a unique index, a mandatory field, a lock) that covers this case rejects the finding.${site ? `
   Where it is practical, show the failure on the test site and record what you ran and what
   came back. Do not force a live proof of a race or an upgrade: a reading is enough there.` : ''}
5. Severity. Assign it yourself from the ladder in the conventions. Do not inherit the reported
   severity: finders overstate.
6. Correct the record. If the finding is real but the file, line, trigger, failure, or impact is
   wrong, confirm it and supply the corrected values.

Default to \`rejected\` when you are unsure. Use \`uncertain\` only when the code is genuinely
ambiguous (an unresolvable dynamic dispatch, core behaviour that depends on a version you cannot
read) and say exactly what you could not resolve. A confirmed finding that turns out to be wrong
costs the maintainer more than a rejected finding that turns out to be real.

${NO_FIXES}`

const checkPrompt = c => {
	const security = c.dir === SEC
	const conventions = security ? `${SEC}/_conventions.md` : `${QUAL}/_audit.md`
	return `You run one whole-surface check over a Frappe app. Your check is ${c.bare}, and only ${c.bare}.

A check is not a bug hunt. It reports the whole surface: a percentage, a diff against a
baseline, or a table. Nothing verifies it afterwards, so everything you report must be something
you read yourself.

1. Read \`${conventions}\` first, in particular the "Two kinds" section. It tells you what a
   check owes and what it does not.
2. Read \`${c.dir}/${c.file}\`. That is your check. Follow its \`Output\` section exactly: that
   table is the deliverable.${security ? '' : `
   The mechanism pages in \`${QUAL}/mechanisms/\` describe how core resolves each mechanism.`}
3. The app checkout is \`${setup.targetDir}\`. Treat it as read-only: change no file in it.

${INV}

${DEPS}

${security ? LIVE_SEC : LIVE_QUAL}

Report \`not applicable\` when the check needs a target this run does not have: a GitHub org, a
DNS zone, a stored baseline, a core checkout. That is a correct result, not a failure. Say in
\`notes\` what you would have needed.

If you find something that clears the four-part bar of the conventions, put it in \`findings\`
and name the scope or rule it belongs to. Nothing verifies these, so state them conservatively.
Do not force a gap into that shape to make the list look longer; a gap belongs in \`gaps\`.

Where your check asks for a desired or recommended value (a header value, a DNS record, a
generator default), give it: a posture table without the target state is not actionable. That is
the only exception. Do not write a patch for application code, and do not propose a remediation
for anything in \`findings\`.`
}

// --- Checks, alongside the scan ---------------------------------------------

const checksRun = checks.length
	? parallel(checks.map(c => () =>
		agent(checkPrompt(c), { label: `check:${c.id}`, phase: 'Check', schema: CHECK_SCHEMA })
			.then(r => (r ? { ...r, id: c.id, track: c.track, title: c.title } : null))))
	: Promise.resolve([])

// --- Scan, then verify each candidate as soon as its prompt lands ------------

// The run has a hard cap of 1000 agents. Scans and checks are few and known up front; the
// verifications are not, so they draw on one shared allowance and every drop is logged.
let verifyAllowance = MAX_VERIFICATIONS

const scanned = await pipeline(
	scopes,

	s => agent(s.kind === 'scope' ? secScanPrompt(s) : qualScanPrompt(s), {
		label: `scan:${s.id}`,
		phase: 'Scan',
		schema: s.kind === 'scope' ? scanSchema(SEC_CANDIDATE, SEC_REQUIRED) : scanSchema(QUAL_CANDIDATE, QUAL_REQUIRED),
	}),

	(scan, s) => {
		if (!scan) return { scope: s, coverage: 'scan agent failed', candidates: [], unverified: 0 }
		// The cap must drop the least severe candidates, not the ones the finder listed last.
		const all = [...(scan.candidates || [])].sort(bySeverity)
		const take = Math.max(0, Math.min(all.length, MAX_CANDIDATES, verifyAllowance))
		verifyAllowance -= take
		const batch = all.slice(0, take)
		if (all.length > batch.length) {
			log(`${s.id}: ${all.length - batch.length} of ${all.length} candidates left unverified (${take < Math.min(all.length, MAX_CANDIDATES) ? `run cap ${MAX_VERIFICATIONS}` : `cap ${MAX_CANDIDATES}`})`)
		}
		if (!batch.length) return { scope: s, coverage: scan.coverage, candidates: [], unverified: all.length }

		return parallel(batch.map(c => () =>
			agent(s.kind === 'scope' ? secVerifyPrompt(s, c) : qualVerifyPrompt(s, c), {
				label: `verify:${s.id}:${c.title.slice(0, 40)}`,
				phase: 'Verify',
				schema: VERDICT_SCHEMA,
			}).then(v => ({ ...c, id: s.id, track: s.track, verdict: v }))
		)).then(verified => ({
			scope: s,
			coverage: scan.coverage,
			candidates: verified.filter(Boolean),
			unverified: all.length - batch.length,
		}))
	}
)

// --- Collect ----------------------------------------------------------------

const rows = scanned.filter(Boolean)
const all = rows.flatMap(r => r.candidates)
const kept = all.filter(c => c.verdict && c.verdict.verdict !== 'rejected')

const pick = (c, key) => (c.verdict[key] || c[key])
const finalised = kept.map(c => ({
	id: c.id,
	track: c.track,
	severity: pick(c, 'severity'),
	title: pick(c, 'title'),
	file: pick(c, 'file'),
	...(c.track === 'security'
		? { actor: pick(c, 'actor'), input: pick(c, 'input'), reachability: c.verdict.reachability, exploit: c.verdict.exploit }
		: { trigger: pick(c, 'trigger'), failure: pick(c, 'failure') }),
	impact: pick(c, 'impact'),
	proof: pick(c, 'proof'),
	verdict: c.verdict.verdict,
	tested: c.verdict.tested === true,
	evidence: c.verdict.evidence,
	reasoning: c.verdict.reasoning,
	corrections: c.verdict.corrections,
	envDependent: c.verdict.envDependent === true,
	envCaveat: c.verdict.envCaveat,
})).sort(bySeverity)

const coverage = rows.map(r => ({
	id: r.scope.id,
	track: r.scope.track,
	title: r.scope.title,
	candidates: r.candidates.length,
	confirmed: r.candidates.filter(c => c.verdict && c.verdict.verdict === 'confirmed').length,
	unverified: r.unverified,
	notes: r.coverage,
}))

const checkResults = (await checksRun).filter(Boolean)
const checkFindings = checkResults.flatMap(r => (r.findings || []).map(f => ({ ...f, from: r.id })))

if (checks.length) {
	log(`${checkResults.length}/${checks.length} checks ran: ${checkResults.map(r => `${r.id} ${r.status}`).join(', ') || 'none'}${checkFindings.length ? `, ${checkFindings.length} unverified findings raised` : ''}`)
}

const countBy = (list, trackName) => {
	const out = { Critical: 0, High: 0, Moderate: 0, Low: 0 }
	list.filter(f => f.track === trackName && f.verdict === 'confirmed').forEach(f => { out[f.severity] = (out[f.severity] || 0) + 1 })
	return out
}
const confirmedCandidatesByTrack = Object.fromEntries(Object.keys(TRACK_NAME).map(t => [t, countBy(finalised, t)]))

const siteInfo = site
	? { site: site.site, baseUrl: site.baseUrl, bench: site.benchDir, created: site.created, dropped: false }
	: { site: null, reason: opts.noSite ? 'skipped by args' : 'could not be built' }

async function dropSite() {
	if (!site || !opts.dropSite || !site.created) return
	await agent(`Tear down the disposable audit site \`${site.site}\` on the bench at \`${site.benchDir}\`.
Stop the \`bench serve\` process on port ${SITE_PORT}, then run
\`bench drop-site ${site.site} --force${opts.dbRootPassword ? ` --db-root-password '${opts.dbRootPassword}'` : ''}\`.
Touch no other site, and change nothing in \`${setup.targetDir}\`. Report what you removed.`, { label: 'drop-site', phase: 'Report' })
	siteInfo.dropped = true
}

log(`${all.length} candidates, ${finalised.filter(f => f.verdict === 'confirmed').length} confirmed, ${all.length - kept.length} refuted, ${finalised.filter(f => f.tested).length} tested live`)

if (!finalised.length && !checkResults.length) {
	await dropSite()
	return {
		app: setup.appName, target: setup.targetDir, commit: setup.commit,
		scans: scopes.length, candidates: all.length, confirmed: 0,
		report: null, coverage, site: siteInfo,
	}
}

// --- Report -----------------------------------------------------------------

phase('Report')

const OUTPUT = opts.output || `${setup.targetDir}/../${setup.appName || 'app'}-deep-audit.md`
const rawPath = `${OUTPUT.replace(/\.md$/, '')}-findings.json`

// The report agent runs last and costs the most context. When it dies, every verified finding
// is stranded in the return value. Land the raw material on disk first, so a failed report is a
// re-run of one agent and not of the audit. The report agent then reads the file, which also
// keeps a large result set out of its prompt.
const persisted = await agent(`Write a JSON file. Do not audit anything, do not summarise, and do not edit the content.

Write exactly the JSON below to \`${rawPath}\`, byte for byte, then confirm the path and the
number of entries in \`findings\`. This is the audit's raw output, kept so that a failure in the
report step does not lose the work behind it.

\`\`\`json
${JSON.stringify({
		app: setup.appName, commit: setup.commit, frameworkVersion: setup.frameworkVersion,
		site: siteInfo, weakenedConfig: WEAKENED || [],
		findings: finalised, checkFindings, coverage, checks: checkResults,
	}, null, 1)}
\`\`\``, { label: 'persist', phase: 'Report' })

const DATA = persisted
	? `The audit's results are in \`${rawPath}\`. It is large: query it with \`jq\` rather than reading
it whole. Its keys:
- \`findings\`: every candidate that survived verification, with \`id\` (the prompt that found it),
  \`track\`, \`severity\`, \`verdict\` (\`confirmed\` or \`uncertain\`), and the finding fields.
- \`checkFindings\`: findings a check raised. Nothing verified these.
- \`coverage\`: one entry per scan: what it searched, what it skipped, and how many candidates
  were left unverified by a cap.
- \`checks\`: one entry per whole-surface check, with its status, summary, table, and gaps.
- \`site\`, \`weakenedConfig\`: how the findings were verified.`
	: `The raw file could not be written, so the results are inline:

\`\`\`json
${JSON.stringify({ site: siteInfo, weakenedConfig: WEAKENED || [], findings: finalised, checkFindings, coverage, checks: checkResults }, null, 1)}
\`\`\``

const report = await agent(`Compile one deep audit report for the Frappe app \`${setup.appName || setup.targetDir}\`.

Write it to \`${OUTPUT}\`. Write nothing inside the app checkout itself.

${DATA}

The audit ran three tracks. Each track has its own finding format, which is the deliverable for
its findings:
- **Security**: the scopes \`S-A01\` to \`S-L02\` and the posture checks \`S-P01\` to \`S-P10\`.
  Format: the "Output" section of \`${SEC}/_conventions.md\`.
- **Correctness**: the rules \`Q-B..\`. Format: the "Output" section of \`${QUAL}/_audit.md\`.
- **Customization**: the rules \`Q-A..\` and the checks \`Q-K..\`. Format: the same as correctness.
Each rule file is in \`${QUAL}/A-customization\` or \`${QUAL}/B-correctness\`; each scope file is in
the area directories of \`${SEC}\`. Read a prompt file when you need its title or its intent.

Assemble the report from these sections, in this order:

- **Header.** The app, the commit (\`${setup.commit || 'unknown'}\`), the Frappe version
   (\`${setup.frameworkVersion || 'unknown'}\`), how many security scopes, quality rules, and checks
   ran, and the count per severity for each track. State how the findings were verified: ${site
		? `against a live test site (\`${site.site}\`, apps: ${(site.installedApps || []).join(', ') || 'unknown'}), so state how many findings carry a recorded result`
		: 'by reading the source only, with no live site, so state that no finding was executed'}.
${WEAKENED && WEAKENED.length ? `
- **Environment**, directly after the header. State that the test site set
   ${WEAKENED.map(c => `\`${c.key}=${c.value}\``).join(', ')}, list which findings depend on that, and say
   plainly that their executed proof does not establish the behaviour of a normally configured
   site. A reader who takes the recorded results at face value must be corrected here, at the top.
` : ''}
- **Summary.** One table over every distinct confirmed finding in all tracks, most severe first:
   number, severity, track, title, and the ids that reached it. This table is the page a reader
   acts on, so keep each title short and exact.

- **Security findings**, then **Correctness findings**, then **Customization findings**. Each
   section holds its confirmed findings, most severe first, in the format of its track, with the
   same numbers as the summary table. When a section is empty, say so in one line.

   Fold by root cause, not by wording. Scopes and rules overlap by design, and several of them
   reach the same defect from different directions: one missing permission hook can arrive as ten
   candidates, and one check-then-insert can arrive from a security scope and a correctness rule.
   Two entries are the same finding when fixing one line fixes both. Merge them into one, list
   every id that reached it, and keep the strongest statement and the best evidence of the set.
   When the entries come from different tracks, put the finding in the track of the highest
   severity and state the other track in one line.

   State the convergence, \`found independently by N prompts\`, for anything reached more than
   twice. It tells the maintainer the defect is hard to miss, which is not the same as severe.

   When folded entries disagree on severity, take the highest and say in one line that the
   verifiers split and what the range was. Never average them, and never quietly pick one.

   Report the distinct count as the headline, with the raw count beside it: \`N findings
   (M confirmed candidates before folding)\`. The raw count is not the result.${site ? `
   Add an \`**Evidence:**\` bullet to every finding whose \`tested\` is true, holding what was run
   and what came back. Mark the rest \`**Evidence:** not executed\`.` : ''}
   Any finding whose \`envDependent\` is true carries its \`envCaveat\` as a bullet on the finding
   itself. Someone triaging one finding in isolation must see it without reading the rest of the
   document, and must see what to re-test before the severity is settled.

- **Unresolved.** The \`uncertain\` verdicts, grouped by track, each with the exact question the
   verifier could not settle. Do not mix these into the confirmed lists.
${checkFindings.length ? `
- **Raised by a check, not verified.** The \`checkFindings\`. Nothing tried to refute these, so
   say that in one line at the top of the section, and never merge them into the confirmed lists.
` : ''}
- **Appendix: coverage.** One table per track: each id, its title, candidates, confirmed, and
   what it searched and skipped. Name every scan whose candidates a cap left unverified.
${checkResults.length ? `
- **Appendix: checks.** One subsection per check, grouped by track, holding its status, its
   summary, and its table verbatim. The tables are the deliverable of those checks. List the
   \`not applicable\` ones in a single line at the end, with the reason from their notes.
` : ''}
Rules:
- Report only what is in the results. Do not add findings, and do not re-audit the app.
- Do not restate the severity of a finding as more or less than the verdict gives it.
- Never pad. If a severity band is empty, say so in one line.
- A check's gap is not a finding. Keep the two apart everywhere in the document.
- For a correctness or customization finding, cite its rule id. The rule shows the accepted
  practice, so the report does not need to.
${NO_FIXES}
The check tables are the exception: where a check recorded a desired or recommended value, keep
it. That is what makes the table readable.

Return the absolute path you wrote and the per-track, per-severity counts of distinct findings.`, { label: 'report', phase: 'Report' })

await dropSite()

return {
	app: setup.appName,
	target: setup.targetDir,
	commit: setup.commit,
	inventory: setup.inventoryPath,
	site: siteInfo,
	scans: scopes.length,
	checks: checkResults.map(r => ({ id: r.id, status: r.status, summary: r.summary, gaps: r.gaps || [] })),
	candidates: all.length,
	confirmed: finalised.filter(f => f.verdict === 'confirmed').length,
	uncertain: finalised.filter(f => f.verdict === 'uncertain').length,
	refuted: all.length - kept.length,
	testedLive: finalised.filter(f => f.tested).length,
	confirmedCandidatesByTrack,
	report: report || `report agent failed; findings are in ${persisted ? rawPath : 'this return value'}`,
	rawFindings: persisted ? rawPath : null,
	findings: finalised,
	checkFindings,
	coverage,
}
