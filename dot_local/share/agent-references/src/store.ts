import {
	lstat,
	mkdir,
	readlink,
	rename,
	rm,
	symlink,
	unlink,
} from "node:fs/promises";
import { dirname, isAbsolute, join, relative } from "node:path";
import {
	errorCode,
	errorMessage,
	isRecord,
	millisSince,
	nowIso,
	omitKey,
	readJson,
} from "./fs.ts";
import { firstLine, git, SHA_PATTERN } from "./git.ts";
import { type Entry, parseRepository, type Remote } from "./manifest.ts";
import { aliasPath, type Paths, treePath } from "./paths.ts";
import {
	type AliasState,
	type AliasStatus,
	emptyAliasState,
	type RefKind,
	type State,
} from "./state.ts";

export const DEFAULT_DEPTH = 100;
const MARKER_TTL_MS = 24 * 60 * 60_000;
const MARKERS = new Bun.Glob("*.json");
const SYMREF_LINE = /^ref: refs\/heads\/(\S+)\tHEAD$/m;
const HEAD_LINE = /^([0-9a-f]{40})\tHEAD$/m;

export interface StoreOptions {
	offline: boolean;
}

export function repoDir(paths: Paths, remote: Remote): string {
	return join(paths.repos, remote.host, remote.owner, `${remote.repo}.git`);
}

interface Resolved {
	kind: RefKind;
	ref: string;
	sha: string;
}

interface Failure {
	error: string;
}

async function ensureRepo(dir: string, remote: Remote): Promise<string | null> {
	if (!(await Bun.file(join(dir, "HEAD")).exists())) {
		await mkdir(dir, { recursive: true });
		const init = await git(["init", "--quiet", "--bare", dir]);
		if (!init.ok) {
			await rm(dir, { force: true, recursive: true });
			return firstLine(init.stderr);
		}
		const add = await git(["remote", "add", "origin", remote.url], {
			cwd: dir,
		});
		return add.ok ? null : firstLine(add.stderr);
	}
	const url = await git(["remote", "get-url", "origin"], { cwd: dir });
	if (!url.ok) {
		const add = await git(["remote", "add", "origin", remote.url], {
			cwd: dir,
		});
		return add.ok ? null : firstLine(add.stderr);
	}
	if (url.stdout !== remote.url) {
		const set = await git(["remote", "set-url", "origin", remote.url], {
			cwd: dir,
		});
		return set.ok ? null : firstLine(set.stderr);
	}
	return null;
}

async function resolveDefaultBranch(dir: string): Promise<Resolved | Failure> {
	const head = await git(["ls-remote", "--symref", "origin", "HEAD"], {
		cwd: dir,
	});
	if (!head.ok) {
		return { error: firstLine(head.stderr) };
	}
	const symref = SYMREF_LINE.exec(head.stdout)?.[1];
	const sha = HEAD_LINE.exec(head.stdout)?.[1];
	if (!(symref && sha)) {
		return { error: "remote HEAD is not a branch; set ref in the manifest" };
	}
	return { kind: "branch", ref: symref, sha };
}

async function resolveRemote(
	dir: string,
	ref: string | undefined
): Promise<Resolved | Failure> {
	if (!ref) {
		return resolveDefaultBranch(dir);
	}
	if (SHA_PATTERN.test(ref)) {
		return { kind: "commit", ref, sha: ref };
	}
	const listed = await git(
		[
			"ls-remote",
			"origin",
			`refs/heads/${ref}`,
			`refs/tags/${ref}`,
			`refs/tags/${ref}^{}`,
		],
		{ cwd: dir }
	);
	if (!listed.ok) {
		return { error: firstLine(listed.stderr) };
	}
	const rows = new Map<string, string>();
	for (const line of listed.stdout.split("\n")) {
		const [sha, name] = line.split("\t");
		if (sha && name) {
			rows.set(name, sha);
		}
	}
	const branch = rows.get(`refs/heads/${ref}`);
	if (branch) {
		return { kind: "branch", ref, sha: branch };
	}
	const tag = rows.get(`refs/tags/${ref}^{}`) ?? rows.get(`refs/tags/${ref}`);
	if (tag) {
		return { kind: "tag", ref, sha: tag };
	}
	return { error: `ref "${ref}" is not a branch or tag on the remote` };
}

async function hasCommit(dir: string, sha: string): Promise<boolean> {
	const result = await git(["cat-file", "-e", `${sha}^{commit}`], { cwd: dir });
	return result.ok;
}

function refspec(resolved: Resolved): string {
	switch (resolved.kind) {
		case "branch":
			return `+refs/heads/${resolved.ref}:refs/remotes/origin/${resolved.ref}`;
		case "tag":
			return `+refs/tags/${resolved.ref}:refs/tags/${resolved.ref}`;
		default:
			return resolved.sha;
	}
}

async function fetchCommit(
	dir: string,
	resolved: Resolved,
	depth: number
): Promise<string | null> {
	if (await hasCommit(dir, resolved.sha)) {
		return null;
	}
	const args = ["fetch", "--quiet", "--no-tags"];
	if (depth > 0) {
		args.push(`--depth=${depth}`);
	}
	const result = await git([...args, "origin", refspec(resolved)], {
		cwd: dir,
	});
	if (!result.ok) {
		return firstLine(result.stderr);
	}
	if (!(await hasCommit(dir, resolved.sha))) {
		return `fetch finished but ${resolved.sha} is absent`;
	}
	return null;
}

function fail(current: AliasState, status: AliasStatus, error: string): void {
	current.status = status;
	current.error = error;
	current.checkedAt = nowIso();
}

export async function currentTree(
	paths: Paths,
	alias: string
): Promise<string | null> {
	const link = aliasPath(paths, alias);
	try {
		if (!(await lstat(link)).isSymbolicLink()) {
			return null;
		}
		const target = await readlink(link);
		return isAbsolute(target) ? target : join(paths.store, target);
	} catch {
		return null;
	}
}

export async function treeExists(
	paths: Paths,
	alias: string,
	head: string | null
): Promise<boolean> {
	if (!head) {
		return false;
	}
	const tree = await currentTree(paths, alias);
	return (
		tree === treePath(paths, alias, head) &&
		(await Bun.file(join(tree, ".git")).exists())
	);
}

async function ensureTree(
	dir: string,
	tree: string,
	sha: string
): Promise<string | null> {
	if (await Bun.file(join(tree, ".git")).exists()) {
		const head = await git(["rev-parse", "HEAD"], { cwd: tree });
		if (head.ok && head.stdout === sha) {
			return null;
		}
		await git(["worktree", "remove", "--force", tree], { cwd: dir });
	}
	await rm(tree, { force: true, recursive: true });
	await git(["worktree", "prune"], { cwd: dir });
	await mkdir(dirname(tree), { recursive: true });
	const add = await git(["worktree", "add", "--detach", "--quiet", tree, sha], {
		cwd: dir,
	});
	return add.ok ? null : firstLine(add.stderr);
}

async function flipSymlink(
	paths: Paths,
	alias: string,
	tree: string
): Promise<void> {
	const link = aliasPath(paths, alias);
	try {
		if (!(await lstat(link)).isSymbolicLink()) {
			throw new Error(`${link} exists and is not a symlink`);
		}
	} catch (error) {
		if (errorCode(error) !== "ENOENT") {
			throw error;
		}
	}
	const temp = join(paths.store, `.${alias}.${Bun.randomUUIDv7()}.tmp`);
	await symlink(relative(paths.store, tree), temp);
	await rename(temp, link);
}

function retire(state: State, tree: string | null): void {
	if (tree && !state.retired.some((item) => item.tree === tree)) {
		state.retired.push({ retiredAt: nowIso(), tree });
	}
}

export async function applyAlias(
	paths: Paths,
	state: State,
	alias: string,
	current: AliasState,
	target: string,
	depth: number,
	options: StoreOptions
): Promise<string | null> {
	let remote: Remote;
	try {
		remote = parseRepository(current.repository);
	} catch (error) {
		return errorMessage(error);
	}
	const dir = repoDir(paths, remote);
	if (!(await hasCommit(dir, target))) {
		if (options.offline) {
			return `commit ${target.slice(0, 7)} is not fetched; run refs sync`;
		}
		const resolved: Resolved = {
			kind: current.refKind ?? "commit",
			ref: current.ref ?? target,
			sha: target,
		};
		const fetchError = await fetchCommit(dir, resolved, depth);
		if (fetchError) {
			return fetchError;
		}
	}
	const tree = treePath(paths, alias, target);
	const treeError = await ensureTree(dir, tree, target);
	if (treeError) {
		return treeError;
	}
	const previous = await currentTree(paths, alias);
	await flipSymlink(paths, alias, tree);
	if (previous !== tree) {
		retire(state, previous);
	}
	current.head = target;
	current.appliedAt = nowIso();
	if (current.remoteHead === target) {
		current.behind = 0;
	}
	if (current.status === "missing") {
		current.status = "ok";
		current.error = undefined;
	}
	return null;
}

async function fetchAlias(
	dir: string,
	current: AliasState,
	entry: Entry,
	depth: number
): Promise<void> {
	const resolved = await resolveRemote(dir, entry.ref);
	if ("error" in resolved) {
		fail(
			current,
			current.head ? "fetch-failed" : "clone-failed",
			resolved.error
		);
		return;
	}
	const fetchError = await fetchCommit(dir, resolved, depth);
	if (fetchError) {
		fail(current, current.head ? "fetch-failed" : "clone-failed", fetchError);
		return;
	}
	let { sha } = resolved;
	if (resolved.kind === "commit") {
		const full = await git(["rev-parse", "--verify", `${sha}^{commit}`], {
			cwd: dir,
		});
		if (full.ok) {
			sha = full.stdout;
		}
	}
	const fetchedAt = nowIso();
	current.ref = resolved.ref;
	current.refKind = resolved.kind;
	current.remoteHead = sha;
	current.fetchedAt = fetchedAt;
	current.checkedAt = fetchedAt;
	current.status = "ok";
	current.error = undefined;
	if (current.head && current.head !== sha) {
		const count = await git(
			["rev-list", "--count", `${current.head}..${sha}`],
			{ cwd: dir }
		);
		current.behind = count.ok ? Number.parseInt(count.stdout, 10) : null;
	} else {
		current.behind = current.head ? 0 : null;
	}
}

async function materialize(
	paths: Paths,
	state: State,
	alias: string,
	current: AliasState,
	depth: number
): Promise<void> {
	if (await treeExists(paths, alias, current.head)) {
		return;
	}
	const offline = { offline: true };
	const { head, remoteHead } = current;
	if (!(head || remoteHead)) {
		fail(current, "missing", "nothing fetched yet");
		return;
	}
	const headError = head
		? await applyAlias(paths, state, alias, current, head, depth, offline)
		: "no applied commit";
	if (headError === null) {
		return;
	}
	const fallbackError =
		remoteHead && remoteHead !== head
			? await applyAlias(
					paths,
					state,
					alias,
					current,
					remoteHead,
					depth,
					offline
				)
			: headError;
	if (fallbackError !== null && current.status === "ok") {
		fail(current, "missing", fallbackError);
	}
}

export async function syncAlias(
	paths: Paths,
	state: State,
	alias: string,
	entry: Entry,
	options: StoreOptions
): Promise<AliasState> {
	const current =
		state.aliases[alias] ??
		emptyAliasState(aliasPath(paths, alias), entry.repository);
	current.path = aliasPath(paths, alias);
	current.repository = entry.repository;
	state.aliases[alias] = current;
	const depth = entry.depth ?? DEFAULT_DEPTH;

	let remote: Remote;
	try {
		remote = parseRepository(entry.repository);
	} catch (error) {
		fail(current, "clone-failed", errorMessage(error));
		return current;
	}
	const dir = repoDir(paths, remote);

	if (!options.offline) {
		const repoError = await ensureRepo(dir, remote);
		if (repoError) {
			fail(current, "clone-failed", repoError);
		} else {
			await fetchAlias(dir, current, entry, depth);
		}
	}
	await materialize(paths, state, alias, current, depth);
	return current;
}

export async function retireAlias(
	paths: Paths,
	state: State,
	alias: string
): Promise<void> {
	retire(state, await currentTree(paths, alias));
	const link = aliasPath(paths, alias);
	try {
		if ((await lstat(link)).isSymbolicLink()) {
			await unlink(link);
		}
	} catch {
		// The link is already gone.
	}
	state.aliases = omitKey(state.aliases, alias);
}

async function markerTrees(
	file: string,
	now: Temporal.Instant
): Promise<string[]> {
	const marker = await readJson(file);
	const updatedAt =
		isRecord(marker) && typeof marker.updatedAt === "string"
			? marker.updatedAt
			: null;
	const age = millisSince(updatedAt, now);
	if (age === null || age > MARKER_TTL_MS) {
		await rm(file, { force: true });
		return [];
	}
	if (!(isRecord(marker) && isRecord(marker.trees))) {
		return [];
	}
	return Object.values(marker.trees).filter(
		(tree): tree is string => typeof tree === "string"
	);
}

async function referencedTrees(
	sessionsDir: string,
	now: Temporal.Instant
): Promise<Set<string>> {
	await mkdir(sessionsDir, { recursive: true });
	const files = [...MARKERS.scanSync({ absolute: true, cwd: sessionsDir })];
	const trees = await Promise.all(files.map((file) => markerTrees(file, now)));
	return new Set(trees.flat());
}

async function removeTree(tree: string): Promise<void> {
	if (await Bun.file(join(tree, ".git")).exists()) {
		const common = await git(["rev-parse", "--git-common-dir"], { cwd: tree });
		if (common.ok) {
			await git(["worktree", "remove", "--force", tree], {
				cwd: common.stdout,
			});
		}
	}
	await rm(tree, { force: true, recursive: true });
}

export async function prune(
	paths: Paths,
	state: State,
	now = Temporal.Now.instant()
): Promise<string[]> {
	const referenced = await referencedTrees(paths.sessions, now);
	const live = new Set(
		Object.entries(state.aliases).map(([alias, item]) =>
			item.head ? treePath(paths, alias, item.head) : ""
		)
	);
	const kept = state.retired.filter(
		(item) => !live.has(item.tree) && referenced.has(item.tree)
	);
	const removed = state.retired
		.filter((item) => !(live.has(item.tree) || referenced.has(item.tree)))
		.map((item) => item.tree);
	await Promise.all(removed.map(removeTree));
	state.retired = kept;
	return removed;
}
