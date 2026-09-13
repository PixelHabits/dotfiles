import { basename, dirname } from "node:path";
import { isRecord, readJson, writeJsonAtomic } from "./fs.ts";

export interface Entry {
	depth?: number;
	description?: string;
	ref?: string;
	repository: string;
}

export type Manifest = Record<string, unknown>;

export const ALIAS_PATTERN = /^[a-z0-9][a-z0-9._-]*$/i;
const RESERVED_ALIASES = new Set(["repos", "trees", "state.json"]);

export function validAlias(alias: string): boolean {
	return (
		ALIAS_PATTERN.test(alias) &&
		!RESERVED_ALIASES.has(alias) &&
		!alias.endsWith(".tmp")
	);
}

export async function readManifest(path: string): Promise<Manifest> {
	const value = await readJson(path);
	if (value === undefined) {
		return {};
	}
	if (!isRecord(value)) {
		throw new Error(`manifest ${path} must be a JSON object keyed by alias`);
	}
	return value;
}

export function writeManifest(path: string, manifest: Manifest): Promise<void> {
	return writeJsonAtomic(path, manifest);
}

export function manifestEntries(manifest: Manifest): Record<string, Entry> {
	const entries: Record<string, Entry> = {};
	for (const [alias, value] of Object.entries(manifest)) {
		if (
			!(
				validAlias(alias) &&
				isRecord(value) &&
				typeof value.repository === "string"
			)
		) {
			continue;
		}
		const entry: Entry = { repository: value.repository };
		if (typeof value.ref === "string" && value.ref !== "") {
			entry.ref = value.ref;
		}
		if (typeof value.description === "string" && value.description !== "") {
			entry.description = value.description;
		}
		if (
			typeof value.depth === "number" &&
			Number.isInteger(value.depth) &&
			value.depth >= 0
		) {
			entry.depth = value.depth;
		}
		entries[alias] = entry;
	}
	return entries;
}

export interface Remote {
	host: string;
	owner: string;
	repo: string;
	url: string;
}

const SSH_PATTERN =
	/^(?:[\w.-]+@)?([\w.-]+):([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/;
const HTTP_PATTERN =
	/^(?:https?|ssh|git):\/\/(?:[\w.-]+@)?([\w.-]+)(?::\d+)?\/([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/;
const SHORT_PATTERN = /^([\w.-]+)\/([\w.-]+?)(?:\.git)?$/;
const HOSTED_PATTERN =
	/^([\w-]+(?:\.[\w-]+)+)\/([\w.-]+)\/([\w.-]+?)(?:\.git)?$/;
const TRAILING_SLASHES = /\/+$/;

function stripGit(name: string): string {
	return name.endsWith(".git") ? name.slice(0, -4) : name;
}

function parseLocal(text: string): Remote {
	const local = text.startsWith("file://")
		? text.slice("file://".length)
		: text;
	const clean = local.replace(TRAILING_SLASHES, "");
	return {
		host: "local",
		owner: basename(dirname(clean)) || "root",
		repo: stripGit(basename(clean)),
		url: text,
	};
}

function match(pattern: RegExp, text: string): string[] | null {
	const found: RegExpExecArray | null = pattern.exec(text);
	return found === null ? null : found.slice(1);
}

export function parseRepository(input: string): Remote {
	const text = input.trim();
	if (text.startsWith("/") || text.startsWith("file://")) {
		return parseLocal(text);
	}
	const http = match(HTTP_PATTERN, text);
	if (http) {
		const [host = "", owner = "", repo = ""] = http;
		return { host, owner, repo, url: text.replace(TRAILING_SLASHES, "") };
	}
	const ssh = text.includes("@") ? match(SSH_PATTERN, text) : null;
	if (ssh) {
		const [host = "", owner = "", repo = ""] = ssh;
		return { host, owner, repo, url: text };
	}
	const shorthand = text.startsWith("github:")
		? text.slice("github:".length)
		: text;
	const hosted = match(HOSTED_PATTERN, shorthand);
	if (hosted) {
		const [host = "", owner = "", repo = ""] = hosted;
		return { host, owner, repo, url: `https://${host}/${owner}/${repo}.git` };
	}
	const short = match(SHORT_PATTERN, shorthand);
	if (short) {
		const [owner = "", repo = ""] = short;
		return {
			host: "github.com",
			owner,
			repo,
			url: `https://github.com/${owner}/${repo}.git`,
		};
	}
	throw new Error(
		`cannot parse repository "${input}"; use owner/repo, github:owner/repo, host/owner/repo, or a URL`
	);
}

export function defaultAlias(remote: Remote): string {
	return remote.repo.toLowerCase();
}
