/**
 * Humanization layer for tool events.
 *
 * Translates raw (toolName, args) pairs into warm, conversational
 * descriptions that non-technical users can understand.
 * Also infers the high-level "phase" from the pattern of tool calls.
 */

// ── Phase Inference ──────────────────────────────────────

export type Phase = "exploring" | "analyzing" | "writing" | "done";

export const PHASE_LABELS: Record<Phase, string> = {
	exploring: "Exploring your projects",
	analyzing: "Analyzing your skills",
	writing: "Writing your resume",
	done: "All done!",
};

/**
 * Infer the current phase based on accumulated activity.
 *
 * Heuristics:
 * - If the model is streaming text, we're in the "writing" phase
 * - If we've seen grep/find or many source-file reads, we're "analyzing"
 * - Otherwise we're still "exploring"
 */
export function inferPhase(
	activity: Array<{ tool: string; detail: string }>,
	isStreamingText: boolean,
): Phase {
	if (isStreamingText) return "writing";

	let sourceReads = 0;
	let hasGrep = false;
	let hasFind = false;

	for (const entry of activity) {
		if (entry.tool === "grep") hasGrep = true;
		if (entry.tool === "bash" && entry.detail.includes("find")) hasFind = true;
		if (
			entry.tool === "read" &&
			!entry.detail.includes("README") &&
			!entry.detail.includes("package.json") &&
			!entry.detail.includes("pyproject")
		) {
			sourceReads++;
		}
	}

	if (hasGrep || hasFind || sourceReads >= 3) return "analyzing";
	return "exploring";
}

// ── Tool Call Humanization ───────────────────────────────

/** Extract just the filename from a path. */
function filename(filePath: string): string {
	const parts = filePath.split("/");
	return parts[parts.length - 1] || filePath;
}

/** Extract a short directory name from a path. */
function dirname(filePath: string): string {
	const parts = filePath.split("/").filter(Boolean);
	if (parts.length <= 2) return parts.join("/");
	return `${parts[parts.length - 2]}/${parts[parts.length - 1]}`;
}

/** Humanize a bash command into conversational text. */
function humanizeBash(command: string): string {
	const cmd = command.trim();

	// ls commands
	if (/^ls\b/.test(cmd)) {
		const dirMatch = cmd.match(/ls\s+(?:-\S+\s+)*(.+)/);
		const dir = dirMatch?.[1]?.trim();
		return dir ? `Browsed files in ${dirname(dir)}` : "Browsed your files";
	}

	// find commands
	if (/^find\b/.test(cmd)) {
		const nameMatch = cmd.match(/-name\s+['"]?\*\.(\w+)['"]?/);
		const extMap: Record<string, string> = {
			py: "Python",
			ts: "TypeScript",
			tsx: "TypeScript",
			js: "JavaScript",
			jsx: "JavaScript",
			go: "Go",
			rs: "Rust",
			java: "Java",
			rb: "Ruby",
			c: "C",
			cpp: "C++",
			cs: "C#",
			swift: "Swift",
			kt: "Kotlin",
		};
		if (nameMatch?.[1]) {
			const lang = extMap[nameMatch[1]] ?? `.${nameMatch[1]}`;
			return `Found ${lang} files`;
		}
		return "Searched for files";
	}

	// git commands
	if (/^git\s+log\b/.test(cmd)) return "Looked at your commit history";
	if (/^git\s+shortlog\b/.test(cmd)) return "Checked who contributed";
	if (/^git\s+diff\b/.test(cmd)) return "Reviewed recent changes";
	if (/^git\s+branch\b/.test(cmd)) return "Checked your branches";
	if (/^git\s+remote\b/.test(cmd)) return "Checked remote repositories";
	if (/^git\b/.test(cmd)) return "Looked at your Git history";

	// cat/head/tail
	if (/^(cat|head|tail)\b/.test(cmd)) {
		const fileMatch = cmd.match(/(?:cat|head|tail)\s+(?:-\S+\s+)*(.+)/);
		const file = fileMatch?.[1]?.trim();
		return file ? `Read ${filename(file)}` : "Read a file";
	}

	// wc (word count / line count)
	if (/^wc\b/.test(cmd)) return "Counted lines of code";

	// tree
	if (/^tree\b/.test(cmd)) return "Mapped your project structure";

	// Generic fallback — show first ~40 chars
	const short = cmd.length > 40 ? `${cmd.slice(0, 37)}...` : cmd;
	return `Ran: ${short}`;
}

/** Humanize a grep/search operation. */
function humanizeGrep(args: Record<string, unknown>): string {
	const pattern = (args.pattern as string) ?? "";

	// Common patterns people search for
	if (/import|require/.test(pattern)) return "Searched for dependencies";
	if (/def |function |class /.test(pattern)) return "Searched for definitions";
	if (/error|exception|catch/.test(pattern)) return "Checked error handling";
	if (/test|spec|describe/.test(pattern)) return "Looked at your tests";
	if (/TODO|FIXME|HACK/.test(pattern)) return "Checked for TODOs";
	if (/api|endpoint|route/.test(pattern)) return "Searched for API routes";

	const short = pattern.length > 30 ? `${pattern.slice(0, 27)}...` : pattern;
	return `Searched for "${short}"`;
}

/** Humanize a read operation. */
function humanizeRead(args: Record<string, unknown>): string {
	const filePath = (args.file_path as string) ?? (args.path as string) ?? "";
	if (!filePath) return "Read a file";

	const name = filename(filePath);

	// Special files get friendlier descriptions
	if (/^README/i.test(name)) return "Took a look at your README";
	if (name === "package.json") return "Checked your package.json";
	if (name === "pyproject.toml") return "Checked your Python project config";
	if (name === "Cargo.toml") return "Checked your Rust project config";
	if (name === "go.mod") return "Checked your Go module config";
	if (name === "Makefile") return "Looked at your build config";
	if (name === "Dockerfile") return "Reviewed your Docker setup";
	if (/\.(yml|yaml)$/i.test(name)) return `Reviewed ${name}`;
	if (/\.env/i.test(name)) return "Checked environment config";
	if (/LICENSE/i.test(name)) return "Noted your license";
	if (/CONTRIBUTING/i.test(name)) return "Read your contributing guide";
	if (/CHANGELOG/i.test(name)) return "Reviewed your changelog";

	return `Read ${name}`;
}

/**
 * Translate a raw tool event into a warm, conversational description.
 */
export function humanizeToolCall(
	toolName: string,
	args: Record<string, unknown>,
): string {
	switch (toolName) {
		case "read":
		case "Read":
			return humanizeRead(args);

		case "bash":
		case "Bash": {
			const command = (args.command as string) ?? "";
			return humanizeBash(command);
		}

		case "grep":
		case "Grep":
		case "rg":
			return humanizeGrep(args);

		case "glob":
		case "Glob": {
			const pattern = (args.pattern as string) ?? "";
			return pattern
				? `Searched for ${pattern} files`
				: "Searched for files";
		}

		case "ls":
		case "Ls": {
			const path = (args.path as string) ?? "";
			return path
				? `Browsed files in ${dirname(path)}`
				: "Browsed your files";
		}

		case "find":
		case "Find": {
			const path = (args.path as string) ?? "";
			return path
				? `Searched in ${dirname(path)}`
				: "Searched for files";
		}

		case "write":
		case "Write":
			return "Preparing output";

		default:
			return `Working (${toolName})`;
	}
}
