import { mkdir, rename } from "node:fs/promises";
import { dirname, join } from "node:path";

export async function readJson(path: string): Promise<unknown> {
	const file = Bun.file(path);
	if (!(await file.exists())) {
		return undefined;
	}
	return file.json();
}

export async function writeJsonAtomic(
	path: string,
	value: unknown
): Promise<void> {
	await mkdir(dirname(path), { recursive: true });
	const temp = join(dirname(path), `.${Bun.randomUUIDv7()}.tmp`);
	await Bun.write(temp, `${JSON.stringify(value, null, 2)}\n`);
	await rename(temp, path);
}

export function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function errorCode(error: unknown): string | undefined {
	return isRecord(error) && typeof error.code === "string"
		? error.code
		: undefined;
}

export function errorMessage(error: unknown): string {
	return error instanceof Error ? error.message : String(error);
}

export function inSequence<T>(
	items: readonly T[],
	work: (item: T) => Promise<void>
): Promise<void> {
	return items.reduce(
		(chain, item) => chain.then(() => work(item)),
		Promise.resolve()
	);
}

export function omitKey<T>(
	record: Record<string, T>,
	key: string
): Record<string, T> {
	return Object.fromEntries(
		Object.entries(record).filter(([name]) => name !== key)
	);
}

export function nowIso(): string {
	return Temporal.Now.instant().round("second").toString();
}

export function millisSince(
	iso: string | null | undefined,
	now = Temporal.Now.instant()
): number | null {
	if (!iso) {
		return null;
	}
	try {
		return now.epochMilliseconds - Temporal.Instant.from(iso).epochMilliseconds;
	} catch {
		return null;
	}
}

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

export function formatAge(
	iso: string | null | undefined,
	now = Temporal.Now.instant()
): string {
	const millis = millisSince(iso, now);
	if (millis === null) {
		return "never";
	}
	if (millis < MINUTE) {
		return "just now";
	}
	if (millis < HOUR) {
		return `${Math.floor(millis / MINUTE)}m ago`;
	}
	if (millis < 2 * DAY) {
		return `${Math.floor(millis / HOUR)}h ago`;
	}
	return `${Math.floor(millis / DAY)}d ago`;
}
