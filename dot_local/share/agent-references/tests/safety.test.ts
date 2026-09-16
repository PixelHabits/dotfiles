import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { mkdir, symlink, utimes } from "node:fs/promises";
import { join } from "node:path";
import { acquireLock, lockHeld, lockHolder } from "../src/lock.ts";
import type { State } from "../src/state.ts";
import { prune } from "../src/store.ts";
import { git, makeRemote, makeSandbox, refs, type Sandbox } from "./helpers.ts";

let sandbox: Sandbox;
beforeEach(async () => {
	sandbox = await makeSandbox();
});
afterEach(async () => {
	await sandbox.cleanup();
});

function retired(...trees: string[]): State {
	return {
		aliases: {},
		retired: trees.map((tree) => ({
			retiredAt: new Date(0).toISOString(),
			tree,
		})),
		syncedAt: null,
	};
}

async function marker(dir: string): Promise<string> {
	await mkdir(dir, { recursive: true });
	const file = join(dir, "keep.txt");
	await Bun.write(file, "keep me\n");
	return file;
}

describe("removal guards", () => {
	test("prune keeps a retired path outside the store and a tree link that resolves elsewhere", async () => {
		const outside = join(sandbox.root, "outside");
		const keep = await marker(outside);
		await mkdir(sandbox.paths.trees, { recursive: true });
		const link = join(sandbox.paths.trees, `library@${"a".repeat(40)}`);
		await symlink(outside, link);
		const state = retired(outside, link);
		expect(await prune(sandbox.paths, state)).toEqual([]);
		expect(state.retired.map((item) => item.tree)).toEqual([outside, link]);
		expect(await Bun.file(keep).text()).toBe("keep me\n");
	});

	test("an unregistered directory under trees is neither pruned nor replaced by a checkout", async () => {
		const remote = await makeRemote(sandbox, "library");
		const sha = await git(sandbox, remote.work, ["rev-parse", "HEAD"]);
		const local = join(sandbox.paths.trees, `library@${sha}`);
		const keep = await marker(local);
		expect(await prune(sandbox.paths, retired(local))).toEqual([]);
		const result = await refs(sandbox, [
			"add",
			remote.bare,
			"--alias",
			"library",
		]);
		expect(result.code).toBe(1);
		expect(result.stdout).toContain("did not create");
		expect(await Bun.file(keep).text()).toBe("keep me\n");
	});
});

describe("lock owner", () => {
	test("a live owner survives any age, including the pid-file format", async () => {
		const owner = await acquireLock(sandbox.paths.lock);
		expect(owner).not.toBeNull();
		await utimes(sandbox.paths.lock, new Date(0), new Date(0));
		expect(await acquireLock(sandbox.paths.lock)).toBeNull();
		expect(await lockHeld(sandbox.paths.lock)).toBe(true);
		expect(await lockHolder(sandbox.paths.lock)).toBe(process.pid);
		await owner?.release();
		await mkdir(sandbox.paths.lock);
		await Bun.write(join(sandbox.paths.lock, "pid"), `${process.pid}\n`);
		await utimes(sandbox.paths.lock, new Date(0), new Date(0));
		expect(await acquireLock(sandbox.paths.lock)).toBeNull();
	});
});
