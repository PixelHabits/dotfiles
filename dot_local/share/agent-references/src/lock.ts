import { mkdir, rm, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import { errorCode } from "./fs.ts";

const STALE_AFTER_MS = 10 * 60_000;

export interface Lock {
	release: () => Promise<void>;
}

function processAlive(pid: number): boolean {
	try {
		process.kill(pid, 0);
		return true;
	} catch (error) {
		return errorCode(error) === "EPERM";
	}
}

async function readPid(dir: string): Promise<number | null> {
	const file = Bun.file(join(dir, "pid"));
	if (!(await file.exists())) {
		return null;
	}
	const pid = Number.parseInt((await file.text()).trim(), 10);
	return Number.isInteger(pid) && pid > 0 ? pid : null;
}

async function lockIsStale(dir: string): Promise<boolean> {
	const info = await stat(dir);
	if (
		Temporal.Now.instant().epochMilliseconds - info.mtimeMs >
		STALE_AFTER_MS
	) {
		return true;
	}
	const pid = await readPid(dir);
	return pid === null || !processAlive(pid);
}

export function lockHolder(dir: string): Promise<number | null> {
	return readPid(dir).catch(() => null);
}

async function claim(dir: string): Promise<Lock | null> {
	try {
		await mkdir(dir);
	} catch (error) {
		if (errorCode(error) === "EEXIST") {
			return null;
		}
		throw error;
	}
	await Bun.write(join(dir, "pid"), `${process.pid}\n`);
	return { release: () => rm(dir, { force: true, recursive: true }) };
}

export async function acquireLock(dir: string): Promise<Lock | null> {
	await mkdir(dirname(dir), { recursive: true });
	const first = await claim(dir);
	if (first) {
		return first;
	}
	const stale = await lockIsStale(dir).catch(() => false);
	if (!stale) {
		return null;
	}
	await rm(dir, { force: true, recursive: true });
	return claim(dir);
}

export async function lockHeld(dir: string): Promise<boolean> {
	try {
		return !(await lockIsStale(dir));
	} catch {
		return false;
	}
}
