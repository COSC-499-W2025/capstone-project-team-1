import { spawn } from "node:child_process";
import { platform } from "node:os";

export const spinnerFrames = [
	"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏",
];

/** Open a URL in the user's default browser (macOS, Linux, Windows). */
export function openInBrowser(url: string): void {
	const os = platform();
	const cmd =
		os === "darwin" ? "open"
		: os === "win32" ? "cmd"
		: "xdg-open";
	const args = os === "win32" ? ["/c", "start", "", url] : [url];
	spawn(cmd, args, { detached: true, stdio: "ignore" }).unref();
}
