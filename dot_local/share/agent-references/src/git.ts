import { errorMessage } from "./fs.ts";

export const GIT_TIMEOUT_MS = 60_000;

export interface ExecResult {
	code: number;
	ok: boolean;
	stderr: string;
	stdout: string;
}

export interface ExecOptions {
	cwd?: string;
	timeoutMs?: number;
}

export async function exec(
	cmd: string[],
	options: ExecOptions = {}
): Promise<ExecResult> {
	const timeoutMs = options.timeoutMs ?? GIT_TIMEOUT_MS;
	let proc: Bun.Subprocess<"ignore", "pipe", "pipe">;
	try {
		proc = Bun.spawn({
			cmd,
			cwd: options.cwd,
			env: { ...Bun.env, GIT_TERMINAL_PROMPT: "0", LC_ALL: "C" },
			killSignal: "SIGKILL",
			stderr: "pipe",
			stdin: "ignore",
			stdout: "pipe",
			timeout: timeoutMs,
		});
	} catch (error) {
		return { code: 127, ok: false, stderr: errorMessage(error), stdout: "" };
	}
	const [stdout, stderr, code] = await Promise.all([
		proc.stdout.text(),
		proc.stderr.text(),
		proc.exited,
	]);
	if (proc.signalCode !== null) {
		const reason =
			proc.signalCode === "SIGKILL"
				? `timed out after ${Math.round(timeoutMs / 1000)}s`
				: `killed by ${proc.signalCode}`;
		return {
			code,
			ok: false,
			stderr: `${cmd[0]} ${cmd[1] ?? ""} ${reason}`,
			stdout,
		};
	}
	return { code, ok: code === 0, stderr: stderr.trim(), stdout: stdout.trim() };
}

export function git(
	args: string[],
	options: ExecOptions = {}
): Promise<ExecResult> {
	return exec(["git", ...args], options);
}

export function firstLine(text: string): string {
	const line = text
		.split("\n")
		.map((part) => part.trim())
		.find((part) => part !== "" && !part.startsWith("From "));
	return line ?? "unknown error";
}

export function shortSha(sha: string | null | undefined): string {
	return sha ? sha.slice(0, 7) : "";
}

export const SHA_PATTERN = /^[0-9a-f]{7,40}$/;
