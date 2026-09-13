import { afterEach, beforeEach, expect, test } from "bun:test";
import { join } from "node:path";
import { acquireLock } from "../src/lock.ts";
import { buildLines, renderDelta, renderFull } from "../src/render.ts";
import { readState } from "../src/state.ts";
import { prune } from "../src/store.ts";
import {
	commit,
	makeRemote,
	makeSandbox,
	refs,
	type Sandbox,
} from "./helpers.ts";

let sandbox: Sandbox;
beforeEach(async () => {
	sandbox = await makeSandbox();
});
afterEach(async () => {
	await sandbox.cleanup();
});

test("advertised paths and session pins survive another session applying updates", async () => {
	const remote = await makeRemote(sandbox, "library", { "README.md": "old" });
	expect(
		(await refs(sandbox, ["add", remote.bare, "--alias", "library"])).code
	).toBe(0);
	const [first] = await buildLines(sandbox.paths);
	if (!first?.tree) {
		throw new Error("initial tree missing");
	}
	expect(first.text).toContain(first.tree);
	await renderFull(sandbox.paths, "session-a");
	await commit(sandbox, remote, "update", { "README.md": "new" });
	expect((await refs(sandbox, ["sync"])).code).toBe(0);
	expect((await refs(sandbox, ["apply", "library"])).code).toBe(0);
	const second = await renderFull(sandbox.paths, "session-b");
	expect(second).not.toContain(first.tree);
	expect(await Bun.file(join(first.tree, "README.md")).text()).toBe("old");
	expect(await renderDelta(sandbox.paths, "session-a")).toBe(second);
	const state = await readState(sandbox.paths.stateFile);
	expect(await prune(sandbox.paths, state)).toEqual([]);
	expect(await Bun.file(join(first.tree, "README.md")).text()).toBe("old");
	expect(await renderDelta(sandbox.paths, "session-a")).toBeNull();
});

test("render publishes the session marker while a sync holds the store lock", async () => {
	const remote = await makeRemote(sandbox, "library");
	expect(
		(await refs(sandbox, ["add", remote.bare, "--alias", "library"])).code
	).toBe(0);
	const sync = await acquireLock(sandbox.paths.lock);
	if (!sync) {
		throw new Error("sync lock missing");
	}
	try {
		expect(await renderFull(sandbox.paths, "session-a")).toContain("- library");
		expect(
			await Bun.file(join(sandbox.paths.sessions, "session-a.json")).exists()
		).toBe(true);
		expect(await renderDelta(sandbox.paths, "session-a")).toBeNull();
	} finally {
		await sync.release();
	}
});

test("render waits for a held marker lock, then publishes the marker", async () => {
	const remote = await makeRemote(sandbox, "library");
	expect(
		(await refs(sandbox, ["add", remote.bare, "--alias", "library"])).code
	).toBe(0);
	const held = await acquireLock(sandbox.paths.markerLock);
	if (!held) {
		throw new Error("marker lock missing");
	}
	const rendering = renderFull(sandbox.paths, "session-a");
	await Bun.sleep(100);
	expect(
		await Bun.file(join(sandbox.paths.sessions, "session-a.json")).exists()
	).toBe(false);
	await held.release();
	expect(await rendering).toContain("- library");
	expect(
		await Bun.file(join(sandbox.paths.sessions, "session-a.json")).exists()
	).toBe(true);
});
