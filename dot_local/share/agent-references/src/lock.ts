import {
	lstat,
	mkdir,
	mkdtemp,
	readdir,
	rename,
	rmdir,
	unlink,
} from "node:fs/promises";
import { dirname, join } from "node:path";
import { errorCode } from "./fs.ts";

const STALE_AFTER_MS = 10 * 60_000;
const OWNER = /^owner-([1-9][0-9]*)-[0-9a-f-]+$/;
const PID = /^[1-9][0-9]*$/;

export interface Lock {
	release: () => Promise<void>;
}

interface Holder {
	file: string | null;
	pid: number | null;
	stale: boolean;
}

function processAlive(pid: number): boolean {
	try {
		process.kill(pid, 0);
		return true;
	} catch (error) {
		return errorCode(error) !== "ESRCH";
	}
}

async function inspect(dir: string): Promise<Holder | null> {
	try {
		const info = await lstat(dir);
		if (!info.isDirectory()) {
			return { file: null, pid: null, stale: false };
		}
		const entries = await readdir(dir, { withFileTypes: true });
		const [entry] = entries;
		if (entries.length === 0) {
			return {
				file: null,
				pid: null,
				stale:
					Temporal.Now.instant().epochMilliseconds - info.mtimeMs >
					STALE_AFTER_MS,
			};
		}
		if (entries.length !== 1 || !entry?.isFile()) {
			return { file: null, pid: null, stale: false };
		}
		const match = OWNER.exec(entry.name);
		// PID-file holders also remain live until their process exits.
		const value =
			match?.[1] ??
			(entry.name === "pid"
				? (await Bun.file(join(dir, "pid")).text()).trim()
				: "");
		const pid = PID.test(value) ? Number(value) : null;
		return {
			file: entry.name,
			pid,
			stale: pid !== null && Number.isSafeInteger(pid) && !processAlive(pid),
		};
	} catch (error) {
		if (errorCode(error) === "ENOENT") {
			return null;
		}
		throw error;
	}
}

// Only remove our immutable filename. A successor has a different filename, and
// rmdir cannot remove its nonempty directory. Never recursively remove a lock.
async function removeOwner(dir: string, file: string | null): Promise<void> {
	const info = await lstat(dir).catch(() => null);
	if (!info?.isDirectory()) {
		return;
	}
	if (file) {
		await unlink(join(dir, file)).catch((error: unknown) => {
			if (errorCode(error) !== "ENOENT") {
				throw error;
			}
		});
	}
	await rmdir(dir).catch((error: unknown) => {
		if (!["ENOENT", "ENOTEMPTY", "EEXIST"].includes(errorCode(error) ?? "")) {
			throw error;
		}
	});
}

export async function lockHolder(dir: string): Promise<number | null> {
	return (await inspect(dir))?.pid ?? null;
}

export async function acquireLock(dir: string): Promise<Lock | null> {
	await mkdir(dirname(dir), { recursive: true });
	const previous = await inspect(dir);
	if (previous && !previous.stale) {
		return null;
	}
	if (previous) {
		await removeOwner(dir, previous.file);
	}
	const staging = await mkdtemp(`${dir}.`);
	const file = `owner-${process.pid}-${Bun.randomUUIDv7()}`;
	try {
		await Bun.write(join(staging, file), "");
		// Publish ownership with the directory; no empty mkdir-to-pid window.
		await rename(staging, dir);
	} catch (error) {
		await removeOwner(staging, file);
		if (["ENOTEMPTY", "EEXIST"].includes(errorCode(error) ?? "")) {
			return null;
		}
		throw error;
	}
	return { release: () => removeOwner(dir, file) };
}

export async function lockHeld(dir: string): Promise<boolean> {
	const holder = await inspect(dir);
	return holder !== null && !holder.stale;
}

export async function acquireLockWithRetry(
	dir: string,
	attempts = 50,
	intervalMs = 20
): Promise<Lock | null> {
	const lock = await acquireLock(dir);
	if (lock || attempts === 0) {
		return lock;
	}
	await Bun.sleep(intervalMs);
	return acquireLockWithRetry(dir, attempts - 1, intervalMs);
}
