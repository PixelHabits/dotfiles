import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { mkdir, readlink, rm, stat } from "node:fs/promises";
import { join } from "node:path";
import { readManifest } from "../src/manifest.ts";
import { HEADER } from "../src/render.ts";
import { readState } from "../src/state.ts";
import {
	aliasState,
	commit,
	git,
	hookInput,
	makeRemote,
	makeSandbox,
	parseHook,
	refs,
	type Sandbox,
	waitUntil,
} from "./helpers.ts";

const ADDED_LINE =
	/^- lib {2}\S+\/references\/lib {2}main@[0-9a-f]{7} {2}fetched just now {2}A test library$/;
const TREE_LINK = /^trees\/lib@[0-9a-f]{40}$/;
const FULL_SHA = /^[0-9a-f]{40}$/;
const FAILED_LINE =
	/- lib {2}\S+ {2}main@[0-9a-f]{7} {2}fetch failed just now: .+/;

let sandbox: Sandbox;

beforeEach(async () => {
	sandbox = await makeSandbox();
});

afterEach(async () => {
	await waitForSync();
	await sandbox.cleanup();
});

async function exists(path: string): Promise<boolean> {
	try {
		await stat(path);
		return true;
	} catch {
		return false;
	}
}

function waitForSync(): Promise<boolean> {
	return waitUntil(async () => !(await exists(sandbox.paths.lock)));
}

function linkTarget(alias: string): Promise<string> {
	return readlink(join(sandbox.paths.store, alias));
}

function lib() {
	return aliasState(sandbox, "lib");
}

async function backdateMarker(
	session: string,
	updatedAt: string
): Promise<void> {
	const path = join(sandbox.paths.sessions, `${session}.json`);
	const marker: unknown = await Bun.file(path).json();
	await Bun.write(
		path,
		JSON.stringify({ ...(typeof marker === "object" ? marker : {}), updatedAt })
	);
}

describe("add", () => {
	test("clones, applies, records the description, and renders the line", async () => {
		const remote = await makeRemote(sandbox, "lib", {
			"package.json": JSON.stringify({
				description: "A test library",
				name: "lib",
			}),
		});
		const result = await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
		expect(result.code).toBe(0);
		const line = result.stdout.trim().split("\n").at(-1);
		expect(line).toMatch(ADDED_LINE);
		expect(await exists(join(sandbox.paths.store, "lib", "package.json"))).toBe(
			true
		);
		expect(await linkTarget("lib")).toMatch(TREE_LINK);
		const manifest = await readManifest(sandbox.paths.manifest);
		expect(manifest.lib).toEqual({
			description: "A test library",
			repository: remote.bare,
		});
		expect((await lib()).status).toBe("ok");
	});

	test("preserves unknown manifest keys and rejects a duplicate alias", async () => {
		const remote = await makeRemote(sandbox, "lib");
		await mkdir(join(sandbox.paths.home, ".agents"), { recursive: true });
		await Bun.write(
			sandbox.paths.manifest,
			JSON.stringify({
				$schema: "https://example.invalid/schema.json",
				notes: { keep: true },
			})
		);
		expect(
			(
				await refs(sandbox, [
					"add",
					remote.bare,
					"--alias",
					"lib",
					"--description",
					"given",
				])
			).code
		).toBe(0);
		const manifest = await readManifest(sandbox.paths.manifest);
		expect(manifest.$schema).toBe("https://example.invalid/schema.json");
		expect(manifest.notes).toEqual({ keep: true });
		expect(manifest.lib).toEqual({
			description: "given",
			repository: remote.bare,
		});
		const duplicate = await refs(sandbox, [
			"add",
			remote.bare,
			"--alias",
			"lib",
		]);
		expect(duplicate.code).toBe(1);
		expect(duplicate.stderr).toContain("already exists");
	});

	test("pins a tag and a commit", async () => {
		const remote = await makeRemote(sandbox, "lib");
		const first = await commit(sandbox, remote, "second");
		await git(sandbox, remote.work, ["tag", "v1.0.0"]);
		await git(sandbox, remote.work, ["push", "--quiet", "origin", "v1.0.0"]);
		await commit(sandbox, remote, "third");
		expect(
			(
				await refs(sandbox, [
					"add",
					remote.bare,
					"--alias",
					"tagged",
					"--ref",
					"v1.0.0",
				])
			).code
		).toBe(0);
		expect(
			(
				await refs(sandbox, [
					"add",
					remote.bare,
					"--alias",
					"pinned",
					"--ref",
					first.slice(0, 10),
				])
			).code
		).toBe(0);
		const tagged = await aliasState(sandbox, "tagged");
		const pinned = await aliasState(sandbox, "pinned");
		expect(tagged.refKind).toBe("tag");
		expect(tagged.head).toBe(first);
		expect(pinned.refKind).toBe("commit");
		expect(pinned.head).toBe(first);
		const rendered = await refs(sandbox, ["render", "--full"]);
		expect(rendered.stdout).toContain(`v1.0.0@${first.slice(0, 7)}`);
	});
});

describe("sync and apply", () => {
	test("detects an upstream commit, leaves the checkout alone, and applies on request", async () => {
		const remote = await makeRemote(sandbox, "lib");
		await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
		const before = await linkTarget("lib");
		const next = await commit(sandbox, remote, "second", { "x.txt": "x\n" });

		const sync = await refs(sandbox, ["sync"]);
		expect(sync.code).toBe(0);
		expect(sync.stdout).toContain("upstream +1");
		expect(await linkTarget("lib")).toBe(before);
		expect((await lib()).remoteHead).toBe(next);
		expect((await lib()).behind).toBe(1);
		const rendered = await refs(sandbox, ["render", "--full"]);
		expect(rendered.stdout).toContain(
			"upstream +1 commits, run `refs apply lib`"
		);
		expect(await exists(join(sandbox.paths.store, "lib", "x.txt"))).toBe(false);

		const apply = await refs(sandbox, ["apply", "lib"]);
		expect(apply.code).toBe(0);
		expect(await linkTarget("lib")).toBe(`trees/lib@${next}`);
		expect(await exists(join(sandbox.paths.store, "lib", "x.txt"))).toBe(true);
		expect(await exists(join(sandbox.paths.store, before))).toBe(true);
		expect(
			(await readState(sandbox.paths.stateFile)).retired.map(
				(item) => item.tree
			)
		).toEqual([join(sandbox.paths.store, before)]);
		expect((await refs(sandbox, ["render", "--full"])).stdout).not.toContain(
			"upstream"
		);
	});

	test("prunes a retired tree only when no fresh session marker references it", async () => {
		const remote = await makeRemote(sandbox, "lib");
		await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
		const oldTree = join(sandbox.paths.store, await linkTarget("lib"));
		await refs(sandbox, ["render", "--full", "--session", "reader"]);
		await commit(sandbox, remote, "second");
		await refs(sandbox, ["sync"]);
		await refs(sandbox, ["apply"]);

		await refs(sandbox, ["sync"]);
		expect(await exists(oldTree)).toBe(true);

		await backdateMarker(
			"reader",
			Temporal.Now.instant().subtract({ hours: 25 }).toString()
		);
		const pruned = await refs(sandbox, ["sync"]);
		expect(pruned.stdout).toContain("pruned 1 old tree");
		expect(await exists(oldTree)).toBe(false);
		expect((await readState(sandbox.paths.stateFile)).retired).toEqual([]);
		expect(await exists(join(sandbox.paths.sessions, "reader.json"))).toBe(
			false
		);
	});

	test("records a fetch failure, renders it, and exits 0", async () => {
		const remote = await makeRemote(sandbox, "lib");
		await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
		await rm(remote.bare, { force: true, recursive: true });
		const sync = await refs(sandbox, ["sync"]);
		expect(sync.code).toBe(0);
		const { status, error, head } = await lib();
		expect(status).toBe("fetch-failed");
		expect(error).toBeString();
		expect(head).toMatch(FULL_SHA);
		const rendered = await refs(sandbox, ["render", "--full"]);
		expect(rendered.stdout).toMatch(FAILED_LINE);
		expect(await exists(join(sandbox.paths.store, "lib", "README.md"))).toBe(
			true
		);
	});

	test("reports a missing tree and materializes it on the next sync", async () => {
		const remote = await makeRemote(sandbox, "lib");
		await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
		await rm(join(sandbox.paths.store, "lib"), { force: true });
		await rm(sandbox.paths.trees, { force: true, recursive: true });
		const rendered = await refs(sandbox, ["render", "--full"]);
		expect(rendered.stdout).toContain("missing, run `refs sync`");
		const sync = await refs(sandbox, ["sync"], {
			env: { REFERENCES_OFFLINE: "1" },
		});
		expect(sync.code).toBe(0);
		expect(await exists(join(sandbox.paths.store, "lib", "README.md"))).toBe(
			true
		);
	});

	test("a held lock stops a second sync and a dead holder is taken over", async () => {
		const remote = await makeRemote(sandbox, "lib");
		await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
		await commit(sandbox, remote, "second");
		await mkdir(sandbox.paths.lock, { recursive: true });
		await Bun.write(join(sandbox.paths.lock, "pid"), `${process.pid}\n`);
		const blocked = await refs(sandbox, ["sync"]);
		expect(blocked.code).toBe(1);
		expect(blocked.stderr).toContain("another sync holds");
		expect((await lib()).behind).toBe(0);

		const zombie = Bun.spawn({
			cmd: ["sleep", "60"],
			stdio: ["ignore", "ignore", "ignore"],
		});
		zombie.kill();
		await zombie.exited;
		await Bun.write(join(sandbox.paths.lock, "pid"), `${zombie.pid}\n`);
		const recovered = await refs(sandbox, ["sync"]);
		expect(recovered.code).toBe(0);
		expect((await lib()).behind).toBe(1);
		expect(await exists(sandbox.paths.lock)).toBe(false);
	});

	test("REFERENCES_OFFLINE=1 skips the network", async () => {
		const remote = await makeRemote(sandbox, "lib");
		await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
		await commit(sandbox, remote, "second");
		const sync = await refs(sandbox, ["sync"], {
			env: { REFERENCES_OFFLINE: "1" },
		});
		expect(sync.code).toBe(0);
		expect(sync.stdout).toContain("offline");
		expect((await lib()).behind).toBe(0);
		expect((await refs(sandbox, ["sync"])).stdout).toContain("upstream +1");
	});

	test("remove drops the alias, unlinks the path, and retires the tree", async () => {
		const remote = await makeRemote(sandbox, "lib");
		await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
		const tree = join(sandbox.paths.store, await linkTarget("lib"));
		const removed = await refs(sandbox, ["remove", "lib"]);
		expect(removed.code).toBe(0);
		expect(await readManifest(sandbox.paths.manifest)).toEqual({});
		expect(await exists(join(sandbox.paths.store, "lib"))).toBe(false);
		expect(
			(await readState(sandbox.paths.stateFile)).retired.map(
				(item) => item.tree
			)
		).toEqual([tree]);
		expect((await refs(sandbox, ["render", "--full"])).stdout).toBe("");
	});
});

describe("render", () => {
	test("delta prints once per session, then nothing until a change", async () => {
		const remote = await makeRemote(sandbox, "lib");
		await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
		const first = await refs(sandbox, ["render", "--delta", "--session", "s1"]);
		expect(first.stdout).toContain(HEADER);
		expect(first.stdout).toContain("- lib ");
		expect(
			(await refs(sandbox, ["render", "--delta", "--session", "s1"])).stdout
		).toBe("");
		expect(
			(await refs(sandbox, ["render", "--delta", "--session", "s2"])).stdout
		).toContain("- lib ");

		await commit(sandbox, remote, "second");
		await refs(sandbox, ["sync"]);
		const moved = await refs(sandbox, ["render", "--delta", "--session", "s1"]);
		expect(moved.stdout).toContain("upstream +1 commits");
		expect(
			(await refs(sandbox, ["render", "--delta", "--session", "s1"])).stdout
		).toBe("");
	});

	test("full render after a full render leaves the next delta empty", async () => {
		const remote = await makeRemote(sandbox, "lib");
		await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
		await refs(sandbox, ["render", "--full", "--session", "s1"]);
		expect(
			(await refs(sandbox, ["render", "--delta", "--session", "s1"])).stdout
		).toBe("");
	});
});

describe("hooks", () => {
	test.each(["claude", "codex"])(
		"%s SessionStart applies pending updates and returns the full block",
		async (harness) => {
			const remote = await makeRemote(sandbox, "lib");
			await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
			const next = await commit(sandbox, remote, "second");
			await refs(sandbox, ["sync"]);
			expect(await linkTarget("lib")).not.toBe(`trees/lib@${next}`);

			const result = await refs(sandbox, ["hook", harness, "SessionStart"], {
				stdin: hookInput("SessionStart", "s1", { source: "startup" }),
			});
			expect(result.code).toBe(0);
			const output = parseHook(result.stdout);
			expect(output.hookEventName).toBe("SessionStart");
			expect(output.additionalContext).toStartWith(HEADER);
			expect(output.additionalContext).toContain(`main@${next.slice(0, 7)}`);
			expect(output.additionalContext).not.toContain("upstream");
			expect(await linkTarget("lib")).toBe(`trees/lib@${next}`);
			await waitForSync();
			expect((await readState(sandbox.paths.stateFile)).syncedAt).toBeString();
		}
	);

	test("SessionStart on compact renders but does not move the checkout", async () => {
		const remote = await makeRemote(sandbox, "lib");
		await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
		const before = await linkTarget("lib");
		await commit(sandbox, remote, "second");
		await refs(sandbox, ["sync"]);
		const result = await refs(sandbox, ["hook", "claude", "SessionStart"], {
			stdin: hookInput("SessionStart", "s1", { source: "compact" }),
		});
		expect(parseHook(result.stdout).additionalContext).toContain(
			"upstream +1 commits"
		);
		expect(await linkTarget("lib")).toBe(before);
	});

	test("UserPromptSubmit returns the delta once and refreshes a stale sync", async () => {
		const remote = await makeRemote(sandbox, "lib");
		await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
		await refs(sandbox, ["hook", "claude", "SessionStart"], {
			stdin: hookInput("SessionStart", "s1", { source: "startup" }),
		});
		await waitForSync();
		const quiet = await refs(sandbox, ["hook", "claude", "UserPromptSubmit"], {
			stdin: hookInput("UserPromptSubmit", "s1", { prompt: "hi" }),
		});
		expect(quiet.code).toBe(0);
		expect(quiet.stdout).toBe("");

		await commit(sandbox, remote, "second");
		const current = await readState(sandbox.paths.stateFile);
		current.syncedAt = Temporal.Now.instant().subtract({ hours: 2 }).toString();
		await Bun.write(sandbox.paths.stateFile, JSON.stringify(current));
		const stale = await refs(sandbox, ["hook", "codex", "UserPromptSubmit"], {
			stdin: hookInput("UserPromptSubmit", "s1", { prompt: "hi" }),
		});
		expect(stale.stdout).toBe("");
		expect(await waitUntil(async () => (await lib()).behind === 1)).toBe(true);
		const moved = await refs(sandbox, ["hook", "claude", "UserPromptSubmit"], {
			stdin: hookInput("UserPromptSubmit", "s1", { prompt: "hi" }),
		});
		expect(parseHook(moved.stdout).additionalContext).toContain(
			"upstream +1 commits"
		);
	});

	test("PostToolUse reacts to refs commands only", async () => {
		const remote = await makeRemote(sandbox, "lib");
		await refs(sandbox, ["add", remote.bare, "--alias", "lib"]);
		const unrelated = await refs(sandbox, ["hook", "claude", "PostToolUse"], {
			stdin: hookInput("PostToolUse", "s1", {
				tool_input: { command: "git status && ls" },
				tool_name: "Bash",
				tool_response: {},
			}),
		});
		expect(unrelated.code).toBe(0);
		expect(unrelated.stdout).toBe("");
		const related = await refs(sandbox, ["hook", "codex", "PostToolUse"], {
			stdin: hookInput("PostToolUse", "s1", {
				tool_input: { command: `refs add ${remote.bare} --alias other` },
				tool_name: "Bash",
			}),
		});
		const output = parseHook(related.stdout);
		expect(output.hookEventName).toBe("PostToolUse");
		expect(output.additionalContext).toContain("- lib ");
	});

	test("unknown harness or malformed stdin exits without touching the store", async () => {
		const bad = await refs(sandbox, ["hook", "cursor", "SessionStart"], {
			stdin: "{}",
		});
		expect(bad.code).toBe(1);
		const empty = await refs(sandbox, ["hook", "claude", "SessionStart"], {
			stdin: "",
		});
		expect(empty.code).toBe(0);
		expect(empty.stdout).toBe("");
	});
});
