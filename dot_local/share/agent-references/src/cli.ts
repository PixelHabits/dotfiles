import { join } from "node:path";
import { parseArgs } from "node:util";
import pkg from "../package.json" with { type: "json" };
import {
	errorMessage,
	inSequence,
	isRecord,
	nowIso,
	omitKey,
	readJson,
} from "./fs.ts";
import { exec, shortSha } from "./git.ts";
import { HARNESSES, parseHookInput, runHook } from "./hooks.ts";
import { acquireLock, lockHolder } from "./lock.ts";
import {
	defaultAlias,
	type Entry,
	manifestEntries,
	parseRepository,
	type Remote,
	readManifest,
	validAlias,
	writeManifest,
} from "./manifest.ts";
import { resolvePaths } from "./paths.ts";
import { buildLine, renderDelta, renderFull } from "./render.ts";
import { readState, type State, writeState } from "./state.ts";
import {
	applyAlias,
	currentTree,
	DEFAULT_DEPTH,
	prune,
	retireAlias,
	syncAlias,
} from "./store.ts";

const USAGE = `refs ${pkg.version}

Usage:
  refs add <repository> [--alias <name>] [--ref <branch|tag|sha>] [--description "..."] [--depth <n>]
  refs remove <alias>
  refs list [--json]
  refs sync [alias...]
  refs apply [alias...]
  refs render (--full | --delta) [--session <id>]
  refs hook <claude|codex> <event>

Repository forms: owner/repo, github:owner/repo, host/owner/repo, or a URL.
REFERENCES_OFFLINE=1 skips every network call.`;

const SYNC_CONCURRENCY = 3;
const DESCRIPTION_TIMEOUT_MS = 15_000;

class UsageError extends Error {}

const paths = resolvePaths();
const offline = Bun.env.REFERENCES_OFFLINE === "1";

async function pool<T>(
	items: readonly T[],
	limit: number,
	work: (item: T) => Promise<void>
): Promise<void> {
	const lanes = Array.from(
		{ length: Math.min(limit, items.length) },
		(_, lane) => items.filter((_item, index) => index % limit === lane)
	);
	await Promise.all(lanes.map((lane) => inSequence(lane, work)));
}

async function withLock<T>(run: () => Promise<T>): Promise<T> {
	const lock = await acquireLock(paths.lock);
	if (!lock) {
		const holder = await lockHolder(paths.lock);
		throw new Error(
			`another sync holds ${paths.lock}${holder ? ` (pid ${holder})` : ""}; retry later`
		);
	}
	try {
		return await run();
	} finally {
		await lock.release();
	}
}

function summarize(state: State, alias: string): string {
	const current = state.aliases[alias];
	if (!current) {
		return `${alias}  not synced`;
	}
	const ref = `${current.ref ?? "default"}@${shortSha(current.head) || "-"}`;
	const upstream =
		current.remoteHead && current.head && current.remoteHead !== current.head
			? `  upstream +${current.behind ?? "?"}`
			: "";
	const error = current.error ? `  ${current.error}` : "";
	return `${alias}  ${ref}  ${current.status}${upstream}${error}`;
}

function selectAliases(
	entries: Record<string, Entry>,
	requested: string[]
): string[] {
	if (requested.length === 0) {
		return Object.keys(entries);
	}
	for (const alias of requested) {
		if (!entries[alias]) {
			throw new UsageError(`unknown alias "${alias}"`);
		}
	}
	return requested;
}

async function syncCommand(requested: string[]): Promise<number> {
	const entries = manifestEntries(await readManifest(paths.manifest));
	const targets = selectAliases(entries, requested);
	return withLock(async () => {
		const state = await readState(paths.stateFile);
		const dropped = Object.keys(state.aliases).filter(
			(alias) => !entries[alias]
		);
		await inSequence(dropped, (alias) => retireAlias(paths, state, alias));
		await pool(targets, SYNC_CONCURRENCY, async (alias) => {
			const entry = entries[alias];
			if (entry) {
				await syncAlias(paths, state, alias, entry, { offline });
				await writeState(paths.stateFile, state);
			}
		});
		const pruned = await prune(paths, state);
		state.syncedAt = nowIso();
		await writeState(paths.stateFile, state);
		for (const alias of targets) {
			console.log(summarize(state, alias));
		}
		if (offline) {
			console.log("offline: network calls skipped");
		}
		if (pruned.length > 0) {
			console.log(
				`pruned ${pruned.length} old tree${pruned.length === 1 ? "" : "s"}`
			);
		}
		return 0;
	});
}

async function applyOne(
	state: State,
	alias: string,
	entry: Entry
): Promise<boolean> {
	const current = state.aliases[alias];
	if (!current?.remoteHead) {
		console.log(`${alias}  not synced yet, run refs sync`);
		return true;
	}
	if (
		current.head === current.remoteHead &&
		(await currentTree(paths, alias))
	) {
		console.log(`${alias}  up to date at ${shortSha(current.head)}`);
		return true;
	}
	const error = await applyAlias(
		paths,
		state,
		alias,
		current,
		current.remoteHead,
		entry.depth ?? DEFAULT_DEPTH,
		{ offline }
	);
	if (error) {
		console.log(`${alias}  apply failed: ${error}`);
		return false;
	}
	console.log(`${alias}  applied ${shortSha(current.head)}`);
	return true;
}

async function applyCommand(requested: string[]): Promise<number> {
	const entries = manifestEntries(await readManifest(paths.manifest));
	const targets = selectAliases(entries, requested);
	return withLock(async () => {
		const state = await readState(paths.stateFile);
		let failures = 0;
		await inSequence(targets, async (alias) => {
			const entry = entries[alias];
			if (entry && !(await applyOne(state, alias, entry))) {
				failures += 1;
			}
		});
		await writeState(paths.stateFile, state);
		return failures === 0 ? 0 : 1;
	});
}

async function lookupDescription(
	remote: Remote,
	alias: string
): Promise<string | undefined> {
	if (remote.host === "github.com" && Bun.which("gh") && !offline) {
		const result = await exec(
			[
				"gh",
				"repo",
				"view",
				`${remote.owner}/${remote.repo}`,
				"--json",
				"description",
				"--jq",
				".description",
			],
			{
				timeoutMs: DESCRIPTION_TIMEOUT_MS,
			}
		);
		if (result.ok && result.stdout !== "") {
			return result.stdout;
		}
	}
	const tree = await currentTree(paths, alias);
	if (tree) {
		const manifest = await readJson(join(tree, "package.json"));
		if (
			isRecord(manifest) &&
			typeof manifest.description === "string" &&
			manifest.description !== ""
		) {
			return manifest.description;
		}
	}
	return undefined;
}

interface AddOptions {
	alias?: string;
	depth?: string;
	description?: string;
	ref?: string;
}

function parseDepth(value: string): number {
	const depth = Number.parseInt(value, 10);
	if (!Number.isInteger(depth) || depth < 0) {
		throw new UsageError(
			"--depth must be a whole number; 0 means full history"
		);
	}
	return depth;
}

async function storeDescription(
	alias: string,
	description: string
): Promise<void> {
	const latest = await readManifest(paths.manifest);
	const stored = latest[alias];
	if (isRecord(stored)) {
		stored.description = description;
		await writeManifest(paths.manifest, latest);
	}
}

async function addCommand(
	repository: string,
	values: AddOptions
): Promise<number> {
	const remote = parseRepository(repository);
	const alias = values.alias ?? defaultAlias(remote);
	if (!validAlias(alias)) {
		throw new UsageError(
			`alias "${alias}" is not valid; use letters, digits, dot, dash, underscore`
		);
	}
	const manifest = await readManifest(paths.manifest);
	if (alias in manifest) {
		throw new UsageError(
			`alias "${alias}" already exists in ${paths.manifest}`
		);
	}
	const entry: Entry = { repository: repository.trim() };
	if (values.ref) {
		entry.ref = values.ref;
	}
	if (values.description) {
		entry.description = values.description;
	}
	if (values.depth !== undefined) {
		entry.depth = parseDepth(values.depth);
	}
	manifest[alias] = entry;
	await writeManifest(paths.manifest, manifest);

	await syncCommand([alias]);

	if (!entry.description) {
		const description = await lookupDescription(remote, alias);
		if (description) {
			entry.description = description;
			await storeDescription(alias, description);
		}
	}
	const state = await readState(paths.stateFile);
	console.log(
		(await buildLine(paths, alias, entry, state.aliases[alias])).text
	);
	return state.aliases[alias]?.status === "ok" ? 0 : 1;
}

async function removeCommand(alias: string): Promise<number> {
	const manifest = await readManifest(paths.manifest);
	if (!(alias in manifest)) {
		throw new UsageError(`alias "${alias}" is not in ${paths.manifest}`);
	}
	await writeManifest(paths.manifest, omitKey(manifest, alias));
	return withLock(async () => {
		const state = await readState(paths.stateFile);
		await retireAlias(paths, state, alias);
		await writeState(paths.stateFile, state);
		console.log(
			`removed ${alias}; the old tree is pruned on the next refs sync`
		);
		return 0;
	});
}

async function listCommand(json: boolean): Promise<number> {
	const entries = manifestEntries(await readManifest(paths.manifest));
	const state = await readState(paths.stateFile);
	if (json) {
		const rows = await Promise.all(
			Object.entries(entries).map(async ([alias, entry]) => [
				alias,
				{
					...entry,
					...state.aliases[alias],
					present: (await currentTree(paths, alias)) !== null,
				},
			])
		);
		console.log(
			JSON.stringify(
				{ references: Object.fromEntries(rows), syncedAt: state.syncedAt },
				null,
				2
			)
		);
		return 0;
	}
	for (const alias of Object.keys(entries)) {
		console.log(summarize(state, alias));
	}
	return 0;
}

interface RenderOptions {
	delta?: boolean;
	full?: boolean;
	session?: string;
}

function renderDeltaFor(session: string | undefined): Promise<string | null> {
	if (!session) {
		throw new UsageError("--delta needs --session <id>");
	}
	return renderDelta(paths, session);
}

async function renderCommand(values: RenderOptions): Promise<number> {
	if (values.full === values.delta) {
		throw new UsageError("pass exactly one of --full or --delta");
	}
	const text = values.delta
		? await renderDeltaFor(values.session)
		: await renderFull(paths, values.session);
	if (text !== null) {
		console.log(text);
	}
	return 0;
}

async function hookCommand(harness: string, event: string): Promise<number> {
	if (!HARNESSES.some((known) => known === harness)) {
		throw new UsageError(`harness must be one of ${HARNESSES.join(", ")}`);
	}
	const raw = await Bun.stdin.text();
	const input = parseHookInput(raw.trim() === "" ? {} : JSON.parse(raw));
	const result = await runHook(event, input, paths);
	if (result) {
		console.log(JSON.stringify(result));
	}
	return 0;
}

function required(value: string | undefined, message: string): string {
	if (!value) {
		throw new UsageError(message);
	}
	return value;
}

function main(argv: string[]): Promise<number> {
	const { values, positionals } = parseArgs({
		allowPositionals: true,
		args: argv,
		options: {
			alias: { type: "string" },
			delta: { type: "boolean" },
			depth: { type: "string" },
			description: { type: "string" },
			full: { type: "boolean" },
			help: { short: "h", type: "boolean" },
			json: { type: "boolean" },
			ref: { type: "string" },
			session: { type: "string" },
			version: { short: "v", type: "boolean" },
		},
	});
	if (values.version) {
		console.log(pkg.version);
		return Promise.resolve(0);
	}
	const [command, ...rest] = positionals;
	if (values.help || !command) {
		console.log(USAGE);
		return Promise.resolve(command ? 0 : 1);
	}
	switch (command) {
		case "add":
			return addCommand(
				required(rest[0], "refs add needs a repository"),
				values
			);
		case "remove":
			return removeCommand(required(rest[0], "refs remove needs an alias"));
		case "list":
			return listCommand(values.json === true);
		case "sync":
			return syncCommand(rest);
		case "apply":
			return applyCommand(rest);
		case "render":
			return renderCommand(values);
		case "hook":
			return hookCommand(
				required(rest[0], "refs hook needs <claude|codex> <event>"),
				required(rest[1], "refs hook needs <claude|codex> <event>")
			);
		default:
			throw new UsageError(`unknown command "${command}"`);
	}
}

try {
	process.exitCode = await main(process.argv.slice(2));
} catch (error) {
	console.error(`refs: ${errorMessage(error)}`);
	if (error instanceof UsageError) {
		console.error(USAGE);
	}
	process.exitCode = 1;
}
