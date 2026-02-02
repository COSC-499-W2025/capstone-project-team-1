import { dirname } from "node:path";
import { homedir } from "node:os";

// ============================================================================
// Path Helpers
// ============================================================================

/**
 * Converts a path to breadcrumb segments for display
 */
export function pathToBreadcrumbs(path: string): string[] {
	if (path === "/") return ["/"];
	const parts = path.split("/").filter(Boolean);
	return ["/", ...parts];
}

/**
 * Formats bytes into human-readable size string
 */
export function formatSize(bytes: number): string {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
	if (bytes < 1024 * 1024 * 1024)
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

/**
 * Shortens a path by replacing home directory with ~
 */
export function shortenPath(fullPath: string): string {
	const home = homedir();
	if (fullPath.startsWith(home)) {
		return fullPath.replace(home, "~");
	}
	return fullPath;
}

/**
 * Gets the parent path of a given path
 */
export function getParentPath(path: string): string {
	return dirname(path);
}

/**
 * Checks if a path is at or above a root path
 */
export function isAtOrAboveRoot(currentPath: string, rootPath: string): boolean {
	return currentPath === rootPath || !currentPath.startsWith(rootPath);
}
