import { inSequence, isRecord, millisSince } from "./fs.ts";
import { acquireLock, lockHeld } from "./lock.ts";
import { manifestEntries, readManifest } from "./manifest.ts";
import type { Paths } from "./paths.ts";
import { renderDelta, renderFull } from "./render.ts";
import { readState, writeState } from "./state.ts";
import { applyAlias, DEFAULT_DEPTH } from "./store.ts";
import { renderWorktrees } from "./worktrees.ts";

export const HARNESSES = ["claude", "codex"] as const;
export type Harness = (typeof HARNESSES)[number];

const SYNC_STALE_MS = 60 * 60_000;
const BOUNDARY_SOURCES = new Set(["startup", "resume"]);
const REFS_COMMAND = /\brefs (add|apply|sync|remove)\b/;

export interface HookInput {
	command?: string;
	cwd?: string;
	session?: string;
	source?: string;
}

export interface HookOutput {
	hookSpecificOutput: { hookEventName: string; additionalContext: string };
}

export function parseHookInput(value: unknown): HookInput {
	if (!isRecord(value)) {
		return {};
	}
	const input: HookInput = {};
	if (typeof value.session_id === "string") {
		input.session = value.session_id;
	}
	if (typeof value.cwd === "string") {
		input.cwd = value.cwd;
	}
	if (typeof value.source === "string") {
		input.source = value.source;
	}
	if (
		isRecord(value.tool_input) &&
		typeof value.tool_input.command === "string"
	) {
		input.command = value.tool_input.command;
	}
	return input;
}

function selfCommand(): string[] {
	const compiled =
		Bun.main.startsWith("/$bunfs/") || Bun.main.startsWith("B:/~BUN/");
	return compiled ? [process.execPath] : [process.execPath, Bun.main];
}

function spawnDetachedSync(): void {
	Bun.spawn({
		cmd: [...selfCommand(), "sync"],
		detached: true,
		env: Bun.env,
		stdio: ["ignore", "ignore", "ignore"],
	}).unref();
}

function output(event: string, context: string | null): HookOutput | null {
	return context === null
		? null
		: {
				hookSpecificOutput: {
					additionalContext: context,
					hookEventName: event,
				},
			};
}

async function applyPending(paths: Paths): Promise<void> {
	const lock = await acquireLock(paths.lock);
	if (!lock) {
		return;
	}
	try {
		const entries = manifestEntries(await readManifest(paths.manifest));
		const state = await readState(paths.stateFile);
		const pending = Object.entries(state.aliases).filter(
			([alias, current]) =>
				entries[alias] &&
				current.status === "ok" &&
				current.head &&
				current.remoteHead &&
				current.head !== current.remoteHead
		);
		await inSequence(pending, async ([alias, current]) => {
			const target = current.remoteHead;
			const entry = entries[alias];
			if (!(target && entry)) {
				return;
			}
			const error = await applyAlias(
				paths,
				state,
				alias,
				current,
				target,
				entry.depth ?? DEFAULT_DEPTH,
				{ offline: true }
			);
			if (error) {
				current.error = error;
			}
		});
		if (pending.length > 0) {
			await writeState(paths.stateFile, state);
		}
	} finally {
		await lock.release();
	}
}

async function syncIsStale(paths: Paths): Promise<boolean> {
	const age = millisSince((await readState(paths.stateFile)).syncedAt);
	return age === null || age > SYNC_STALE_MS;
}

async function sessionStart(
	paths: Paths,
	input: HookInput,
	session: string
): Promise<HookOutput | null> {
	if (BOUNDARY_SOURCES.has(input.source ?? "")) {
		await applyPending(paths);
	}
	const blocks = [
		await renderFull(paths, session),
		await renderWorktrees(input.cwd ?? process.cwd()),
	].filter((item) => item !== null);
	const result = output(
		"SessionStart",
		blocks.length === 0 ? null : blocks.join("\n")
	);
	spawnDetachedSync();
	return result;
}

async function userPromptSubmit(
	paths: Paths,
	session: string
): Promise<HookOutput | null> {
	const result = output("UserPromptSubmit", await renderDelta(paths, session));
	if ((await syncIsStale(paths)) && !(await lockHeld(paths.lock))) {
		spawnDetachedSync();
	}
	return result;
}

async function postToolUse(
	paths: Paths,
	input: HookInput,
	session: string
): Promise<HookOutput | null> {
	if (input.command === undefined || !REFS_COMMAND.test(input.command)) {
		return null;
	}
	return output("PostToolUse", await renderDelta(paths, session));
}

export function runHook(
	event: string,
	input: HookInput,
	paths: Paths
): Promise<HookOutput | null> {
	const session = input.session ?? "unknown";
	switch (event) {
		case "SessionStart":
			return sessionStart(paths, input, session);
		case "UserPromptSubmit":
			return userPromptSubmit(paths, session);
		case "PostToolUse":
			return postToolUse(paths, input, session);
		default:
			return Promise.resolve(null);
	}
}
