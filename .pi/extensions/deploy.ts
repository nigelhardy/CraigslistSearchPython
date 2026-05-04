/**
 * Deploy extension for CraigslistSearchPython
 *
 * SSHes into hardleeauto and pulls the latest master branch.
 *
 * Usage (in pi):
 *   /deploy
 */

import { spawn } from "node:child_process";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const REMOTE = "hardleeauto";
const REMOTE_DIR = "~/CraigslistSearchPython";

function sshRun(remote: string, command: string): Promise<{ stdout: string; stderr: string; code: number }> {
	return new Promise((resolve) => {
		const child = spawn("ssh", ["-o", "BatchMode=yes", "-o", "ConnectTimeout=15", remote, command], {
			stdio: ["ignore", "pipe", "pipe"],
		});
		const outChunks: Buffer[] = [];
		const errChunks: Buffer[] = [];
		child.stdout.on("data", (d: Buffer) => outChunks.push(d));
		child.stderr.on("data", (d: Buffer) => errChunks.push(d));
		child.on("error", (e) => resolve({ stdout: "", stderr: e.message, code: 1 }));
		child.on("close", (code) => {
			resolve({
				stdout: Buffer.concat(outChunks).toString().trim(),
				stderr: Buffer.concat(errChunks).toString().trim(),
				code: code ?? 1,
			});
		});
	});
}

export default function (pi: ExtensionAPI) {
	pi.registerCommand("deploy", {
		description: `SSH into ${REMOTE} and git pull latest master in ${REMOTE_DIR}`,
		handler: async (_args, ctx) => {
			ctx.ui.notify(`Deploying to ${REMOTE}…`, "info");
			ctx.ui.setStatus("deploy", `Deploying → ${REMOTE}`);

			const pullCmd = [
				`cd ${REMOTE_DIR}`,
				"git fetch --prune origin",
				"git checkout master 2>/dev/null || git checkout main",
				"git pull --ff-only origin $(git rev-parse --abbrev-ref HEAD)",
				"echo '---'",
				"git log -1 --oneline",
			].join(" && ");

			const result = await sshRun(REMOTE, pullCmd);

			ctx.ui.setStatus("deploy", "");

			const combined = [result.stdout, result.stderr].filter(Boolean).join("\n");

			if (result.code === 0) {
				ctx.ui.notify(`✓ Deploy succeeded on ${REMOTE}`, "success");
				console.log(`\n[deploy] Output from ${REMOTE}:\n${combined}\n`);
			} else {
				ctx.ui.notify(`✗ Deploy failed on ${REMOTE} (exit ${result.code})`, "error");
				console.error(`\n[deploy] Error output from ${REMOTE}:\n${combined}\n`);
			}
		},
	});
}
