import { mkdir, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { isRecord } from "../src/fs.ts";
import { resolvePaths } from "../src/paths.ts";
import type { AliasState } from "../src/state.ts";
import { readState } from "../src/state.ts";

export const CLI = join(import.meta.dir, "../src/cli.ts");

export interface Sandbox {
	cleanup: () => Promise<void>;
	env: Record<string, string>;
	paths: ReturnType<typeof resolvePaths>;
	root: string;
}

export async function makeSandbox(): Promise<Sandbox> {
	const root = await mkdtemp(join(Bun.env.TMPDIR ?? tmpdir(), "refs-test-"));
	const home = join(root, "home");
	await mkdir(home, { recursive: true });
	const env: Record<string, string> = {
		GIT_AUTHOR_EMAIL: "test@example.invalid",
		GIT_AUTHOR_NAME: "Test",
		GIT_COMMITTER_EMAIL: "test@example.invalid",
		GIT_COMMITTER_NAME: "Test",
		GIT_CONFIG_NOSYSTEM: "1",
		HOME: home,
		PATH: Bun.env.PATH ?? "/usr/bin:/bin",
		XDG_CONFIG_HOME: join(home, ".config"),
		XDG_DATA_HOME: join(home, ".local/share"),
		XDG_STATE_HOME: join(home, ".local/state"),
	};
	return {
		cleanup: () => rm(root, { force: true, recursive: true }),
		env,
		paths: resolvePaths(env),
		root,
	};
}

export interface RunResult {
	code: number;
	stderr: string;
	stdout: string;
}

export async function run(
	cmd: string[],
	options: { env: Record<string, string>; cwd?: string; stdin?: string }
): Promise<RunResult> {
	const proc = Bun.spawn({
		cmd,
		cwd: options.cwd,
		env: options.env,
		stderr: "pipe",
		stdin:
			options.stdin === undefined
				? "ignore"
				: new TextEncoder().encode(options.stdin),
		stdout: "pipe",
	});
	const [stdout, stderr, code] = await Promise.all([
		proc.stdout.text(),
		proc.stderr.text(),
		proc.exited,
	]);
	return { code, stderr, stdout };
}

export function refs(
	sandbox: Sandbox,
	args: string[],
	options: { stdin?: string; env?: Record<string, string> } = {}
): Promise<RunResult> {
	return run(["bun", CLI, ...args], {
		cwd: sandbox.root,
		env: { ...sandbox.env, ...options.env },
		stdin: options.stdin,
	});
}

export async function git(
	sandbox: Sandbox,
	cwd: string,
	args: string[]
): Promise<string> {
	const result = await run(["git", ...args], { cwd, env: sandbox.env });
	if (result.code !== 0) {
		throw new Error(`git ${args.join(" ")} failed: ${result.stderr}`);
	}
	return result.stdout.trim();
}

export interface Remote {
	bare: string;
	work: string;
}

export async function makeRemote(
	sandbox: Sandbox,
	name: string,
	files: Record<string, string> = {}
): Promise<Remote> {
	const work = join(sandbox.root, "remotes", `${name}-work`);
	const bare = join(sandbox.root, "remotes", `${name}.git`);
	await mkdir(work, { recursive: true });
	await git(sandbox, sandbox.root, [
		"init",
		"--quiet",
		"--bare",
		"-b",
		"main",
		bare,
	]);
	await git(sandbox, sandbox.root, ["init", "--quiet", "-b", "main", work]);
	await git(sandbox, work, ["remote", "add", "origin", bare]);
	const seed =
		Object.keys(files).length === 0 ? { "README.md": `# ${name}\n` } : files;
	await commit(sandbox, { bare, work }, "initial", seed);
	return { bare, work };
}

export async function commit(
	sandbox: Sandbox,
	remote: Remote,
	message: string,
	files: Record<string, string> = {}
): Promise<string> {
	await Promise.all(
		Object.entries(files).map(([name, content]) =>
			Bun.write(join(remote.work, name), content)
		)
	);
	await git(sandbox, remote.work, ["add", "--all"]);
	await git(sandbox, remote.work, [
		"commit",
		"--quiet",
		"--allow-empty",
		"-m",
		message,
	]);
	await git(sandbox, remote.work, ["push", "--quiet", "origin", "main"]);
	return git(sandbox, remote.work, ["rev-parse", "HEAD"]);
}

export async function aliasState(
	sandbox: Sandbox,
	alias: string
): Promise<AliasState> {
	const current = (await readState(sandbox.paths.stateFile)).aliases[alias];
	if (!current) {
		throw new Error(`alias ${alias} is not in state.json`);
	}
	return current;
}

export function waitUntil(
	condition: () => Promise<boolean>,
	attempts = 100,
	intervalMs = 50
): Promise<boolean> {
	return condition().then(async (done) => {
		if (done) {
			return true;
		}
		if (attempts === 0) {
			return false;
		}
		await Bun.sleep(intervalMs);
		return waitUntil(condition, attempts - 1, intervalMs);
	});
}

export function hookInput(
	event: string,
	session: string,
	extra: Record<string, unknown> = {}
): string {
	return JSON.stringify({
		cwd: "/",
		hook_event_name: event,
		session_id: session,
		...extra,
	});
}

export interface HookOutput {
	additionalContext: string;
	hookEventName: string;
}

export function parseHook(stdout: string): HookOutput {
	const parsed: unknown = JSON.parse(stdout);
	if (!(isRecord(parsed) && isRecord(parsed.hookSpecificOutput))) {
		throw new Error(`unexpected hook output: ${stdout}`);
	}
	const { hookEventName, additionalContext } = parsed.hookSpecificOutput;
	if (
		typeof hookEventName !== "string" ||
		typeof additionalContext !== "string"
	) {
		throw new Error(`unexpected hook output: ${stdout}`);
	}
	return { additionalContext, hookEventName };
}
