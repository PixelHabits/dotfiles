import { isRecord, readJson, writeJsonAtomic } from "./fs.ts";

export const ALIAS_STATUSES = [
	"ok",
	"fetch-failed",
	"clone-failed",
	"missing",
] as const;
export type AliasStatus = (typeof ALIAS_STATUSES)[number];
export const REF_KINDS = ["branch", "tag", "commit"] as const;
export type RefKind = (typeof REF_KINDS)[number];

export interface AliasState {
	appliedAt: string | null;
	behind: number | null;
	checkedAt: string | null;
	error?: string;
	fetchedAt: string | null;
	head: string | null;
	path: string;
	ref: string | null;
	refKind: RefKind | null;
	remoteHead: string | null;
	repository: string;
	status: AliasStatus;
}

export interface Retired {
	retiredAt: string;
	tree: string;
}

export interface State {
	aliases: Record<string, AliasState>;
	retired: Retired[];
	syncedAt: string | null;
}

export function emptyAliasState(path: string, repository: string): AliasState {
	return {
		appliedAt: null,
		behind: null,
		checkedAt: null,
		fetchedAt: null,
		head: null,
		path,
		ref: null,
		refKind: null,
		remoteHead: null,
		repository,
		status: "missing",
	};
}

function optionalString(value: unknown): string | null {
	return typeof value === "string" ? value : null;
}

function isOneOf<T extends string>(
	values: readonly T[],
	value: unknown
): value is T {
	return (
		typeof value === "string" && values.some((candidate) => candidate === value)
	);
}

function parseAliasState(value: unknown): AliasState | null {
	if (
		!(
			isRecord(value) &&
			typeof value.path === "string" &&
			typeof value.repository === "string"
		)
	) {
		return null;
	}
	const state: AliasState = {
		appliedAt: optionalString(value.appliedAt),
		behind: typeof value.behind === "number" ? value.behind : null,
		checkedAt: optionalString(value.checkedAt),
		fetchedAt: optionalString(value.fetchedAt),
		head: optionalString(value.head),
		path: value.path,
		ref: optionalString(value.ref),
		refKind: isOneOf(REF_KINDS, value.refKind) ? value.refKind : null,
		remoteHead: optionalString(value.remoteHead),
		repository: value.repository,
		status: isOneOf(ALIAS_STATUSES, value.status) ? value.status : "missing",
	};
	if (typeof value.error === "string") {
		state.error = value.error;
	}
	return state;
}

function parseRetired(value: unknown): Retired[] {
	if (!Array.isArray(value)) {
		return [];
	}
	const retired: Retired[] = [];
	for (const item of value) {
		if (
			isRecord(item) &&
			typeof item.tree === "string" &&
			typeof item.retiredAt === "string"
		) {
			retired.push({ retiredAt: item.retiredAt, tree: item.tree });
		}
	}
	return retired;
}

export async function readState(path: string): Promise<State> {
	const value = await readJson(path);
	const state: State = { aliases: {}, retired: [], syncedAt: null };
	if (!isRecord(value)) {
		return state;
	}
	state.syncedAt = optionalString(value.syncedAt);
	state.retired = parseRetired(value.retired);
	if (isRecord(value.aliases)) {
		for (const [alias, item] of Object.entries(value.aliases)) {
			const parsed = parseAliasState(item);
			if (parsed) {
				state.aliases[alias] = parsed;
			}
		}
	}
	return state;
}

export function writeState(path: string, state: State): Promise<void> {
	return writeJsonAtomic(path, state);
}
