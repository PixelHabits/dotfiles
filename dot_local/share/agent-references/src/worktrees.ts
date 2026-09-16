import { stat } from "node:fs/promises";
import { isAbsolute, join, relative, resolve } from "node:path";
import { git, shortSha } from "./git.ts";

const MAX_LINES = 40;
const GIT_TIMEOUT_MS = 5000;
const HEADS_PREFIX = /^refs\/heads\//;

interface Worktree {
	bare: boolean;
	branch: string | null;
	head: string | null;
	path: string;
}

async function isDirectory(path: string): Promise<boolean> {
	try {
		return (await stat(path)).isDirectory();
	} catch {
		return false;
	}
}

async function commonDir(cwd: string): Promise<string | null> {
	const bare = join(cwd, ".bare");
	if (await isDirectory(bare)) {
		return bare;
	}
	const result = await git(["rev-parse", "--git-common-dir"], {
		cwd,
		timeoutMs: GIT_TIMEOUT_MS,
	});
	if (!result.ok || result.stdout === "") {
		return null;
	}
	return isAbsolute(result.stdout)
		? result.stdout
		: resolve(cwd, result.stdout);
}

function parsePorcelain(text: string): Worktree[] {
	const entries: Worktree[] = [];
	let current: Worktree | null = null;
	for (const line of text.split("\n")) {
		if (line.startsWith("worktree ")) {
			current = {
				bare: false,
				branch: null,
				head: null,
				path: line.slice("worktree ".length),
			};
			entries.push(current);
		} else if (current && line.startsWith("HEAD ")) {
			current.head = line.slice("HEAD ".length);
		} else if (current && line.startsWith("branch ")) {
			current.branch = line.slice("branch ".length).replace(HEADS_PREFIX, "");
		} else if (current && line === "bare") {
			current.bare = true;
		}
	}
	return entries.filter((entry) => !entry.bare);
}

function displayPath(cwd: string, path: string): string {
	const rel = relative(cwd, path);
	if (rel === "") {
		return ".";
	}
	return rel.startsWith("..") || isAbsolute(rel) ? path : rel;
}

export async function renderWorktrees(cwd: string): Promise<string | null> {
	if (!(await isDirectory(cwd))) {
		return null;
	}
	const dir = await commonDir(cwd);
	if (!dir) {
		return null;
	}
	const listed = await git(
		["--git-dir", dir, "worktree", "list", "--porcelain"],
		{ cwd, timeoutMs: GIT_TIMEOUT_MS }
	);
	if (!listed.ok) {
		return null;
	}
	const lines = parsePorcelain(listed.stdout)
		.map(
			(entry) =>
				`- ${displayPath(cwd, entry.path)}  ${entry.branch ?? `detached@${shortSha(entry.head)}`}`
		)
		.sort((left, right) => left.localeCompare(right))
		.slice(0, MAX_LINES);
	if (lines.length === 0) {
		return null;
	}
	return ["<worktrees>", ...lines, "</worktrees>"].join("\n");
}
