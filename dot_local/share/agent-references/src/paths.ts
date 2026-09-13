import { homedir } from "node:os";
import { join } from "node:path";

export interface Paths {
	home: string;
	lock: string;
	manifest: string;
	repos: string;
	sessions: string;
	stateFile: string;
	store: string;
	trees: string;
}

export function resolvePaths(
	env: Record<string, string | undefined> = Bun.env
): Paths {
	const home = env.HOME ?? homedir();
	const data = env.XDG_DATA_HOME ?? join(home, ".local/share");
	const state = env.XDG_STATE_HOME ?? join(home, ".local/state");
	const store = join(data, "references");
	const stateDir = join(state, "references");
	return {
		home,
		lock: join(stateDir, "sync.lock"),
		manifest: join(home, ".agents/references.json"),
		repos: join(store, "repos"),
		sessions: join(stateDir, "sessions"),
		stateFile: join(store, "state.json"),
		store,
		trees: join(store, "trees"),
	};
}

export function aliasPath(paths: Paths, alias: string): string {
	return join(paths.store, alias);
}

export function treePath(paths: Paths, alias: string, sha: string): string {
	return join(paths.trees, `${alias}@${sha}`);
}
