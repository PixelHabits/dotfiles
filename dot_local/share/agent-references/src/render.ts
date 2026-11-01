import { join } from "node:path";
import {
	formatAge,
	isRecord,
	nowIso,
	readJson,
	writeJsonAtomic,
} from "./fs.ts";
import { shortSha } from "./git.ts";
import { acquireLockWithRetry } from "./lock.ts";
import { type Entry, manifestEntries, readManifest } from "./manifest.ts";
import { aliasPath, type Paths, treePath } from "./paths.ts";
import { type AliasState, emptyAliasState, readState } from "./state.ts";
import { treeExists } from "./store.ts";

export const HEADER = [
	"<available_references>",
	"Read the friendly manual. Before you build with or answer about a library below, read",
	"its source and its own docs (README, docs/, examples, changelog) in the path given.",
	"These libraries move faster than training data. Do not infer an API from patterns you",
	"remember or from other repositories. Cite the file and line you read.",
].join("\n");
export const FOOTER = "</available_references>";

export interface Line {
	alias: string;
	key: string;
	text: string;
	tree: string | null;
}

interface Marker {
	lines: Record<string, string>;
	trees: Record<string, string>;
	updatedAt: string;
}

const AGE_PLACEHOLDER = "<age>";

function describe(
	alias: string,
	entry: Entry,
	current: AliasState,
	present: boolean,
	age: (iso: string | null) => string
): string {
	const ref = current.ref ?? entry.ref ?? "default";
	const parts = [
		`- ${alias}`,
		current.path,
		current.head ? `${ref}@${shortSha(current.head)}` : ref,
	];
	if (!present) {
		parts.push("missing, run `refs sync`");
	} else if (
		current.status === "fetch-failed" ||
		current.status === "clone-failed"
	) {
		parts.push(
			`fetch failed ${age(current.checkedAt)}: ${current.error ?? "unknown error"}`
		);
	} else {
		parts.push(`fetched ${age(current.fetchedAt)}`);
	}
	if (
		present &&
		current.remoteHead &&
		current.head &&
		current.remoteHead !== current.head
	) {
		const behind = current.behind === null ? "?" : String(current.behind);
		parts.push(`upstream +${behind} commits, run \`refs apply ${alias}\``);
	}
	if (entry.description) {
		parts.push(entry.description);
	}
	return parts.join("  ");
}

export async function buildLine(
	paths: Paths,
	alias: string,
	entry: Entry,
	current: AliasState | undefined,
	now = Temporal.Now.instant()
): Promise<Line> {
	const state =
		current ?? emptyAliasState(aliasPath(paths, alias), entry.repository);
	const present = await treeExists(paths, alias, state.head);
	const tree =
		present && state.head ? treePath(paths, alias, state.head) : null;
	const visible = { ...state, path: tree ?? state.path };
	return {
		alias,
		key: describe(alias, entry, visible, present, () => AGE_PLACEHOLDER),
		text: describe(alias, entry, visible, present, (iso) =>
			formatAge(iso, now)
		),
		tree,
	};
}

export async function buildLines(
	paths: Paths,
	now = Temporal.Now.instant()
): Promise<Line[]> {
	const entries = manifestEntries(await readManifest(paths.manifest));
	const state = await readState(paths.stateFile);
	return Promise.all(
		Object.entries(entries).map(([alias, entry]) =>
			buildLine(paths, alias, entry, state.aliases[alias], now)
		)
	);
}

export function block(lines: Line[]): string {
	return [HEADER, ...lines.map((line) => line.text), FOOTER].join("\n");
}

function markerPath(paths: Paths, session: string): string {
	return join(paths.sessions, `${session.replace(/[^\w.-]/g, "_")}.json`);
}

function stringRecord(value: unknown): Record<string, string> {
	const record: Record<string, string> = {};
	if (isRecord(value)) {
		for (const [key, item] of Object.entries(value)) {
			if (typeof item === "string") {
				record[key] = item;
			}
		}
	}
	return record;
}

async function readMarker(
	paths: Paths,
	session: string
): Promise<Marker | null> {
	const value = await readJson(markerPath(paths, session));
	if (!(isRecord(value) && isRecord(value.lines))) {
		return null;
	}
	return {
		lines: stringRecord(value.lines),
		trees: stringRecord(value.trees),
		updatedAt: typeof value.updatedAt === "string" ? value.updatedAt : "",
	};
}

async function writeMarker(
	paths: Paths,
	session: string,
	lines: Line[]
): Promise<void> {
	const previous = await readMarker(paths, session);
	const marker: Marker = {
		lines: {},
		trees: { ...previous?.trees },
		updatedAt: nowIso(),
	};
	for (const line of lines) {
		marker.lines[line.alias] = line.key;
		if (line.tree) {
			marker.trees[line.tree] = line.tree;
		}
	}
	return writeJsonAtomic(markerPath(paths, session), marker);
}

async function render(
	paths: Paths,
	session: string | undefined,
	delta: boolean
): Promise<string | null> {
	const lock = session ? await acquireLockWithRetry(paths.markerLock) : null;
	try {
		const lines = await buildLines(paths);
		const previous = session ? await readMarker(paths, session) : null;
		const visible = delta
			? lines.filter((line) => previous?.lines[line.alias] !== line.key)
			: lines;
		if (session && lock) {
			await writeMarker(paths, session, lines);
		}
		return visible.length === 0 ? null : block(visible);
	} finally {
		await lock?.release();
	}
}

export function renderFull(
	paths: Paths,
	session?: string
): Promise<string | null> {
	return render(paths, session, false);
}

export function renderDelta(
	paths: Paths,
	session: string
): Promise<string | null> {
	return render(paths, session, true);
}
