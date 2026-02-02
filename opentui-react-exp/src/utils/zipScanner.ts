import { fdir } from "fdir";
import { stat } from "node:fs/promises";
import { dirname, basename, join, sep } from "node:path";

// ============================================================================
// Types
// ============================================================================

export type ZipFile = {
	name: string;
	fullPath: string;
	size?: number;
	parentDir: string;
};

export type DirEntry = {
	name: string;
	fullPath: string;
	zipCount: number;
	isParent?: boolean;
};

export type ScanOptions = {
	rootPath: string;
	excludeDirs?: string[];
};

export type ScanResult = {
	zips: ZipFile[];
	error?: string;
};

// ============================================================================
// Default exclusions
// ============================================================================

export const DEFAULT_EXCLUDE_DIRS = [
	"node_modules",
	".git",
	".Trash",
	"Library",
	"System",
	"Applications",
	".cache",
	".npm",
	".bun",
	".vscode",
	".idea",
];

// ============================================================================
// ZIP Scanner
// ============================================================================

/**
 * Scans a directory for all ZIP files using fdir
 */
export async function scanForZips(options: ScanOptions): Promise<ScanResult> {
	const { rootPath, excludeDirs = DEFAULT_EXCLUDE_DIRS } = options;

	try {
		const crawler = new fdir()
			.withFullPaths()
			.filter((path) => path.toLowerCase().endsWith(".zip"))
			.exclude((dirName) => excludeDirs.includes(dirName))
			.crawl(rootPath);

		const files = await crawler.withPromise();

		// Convert to ZipFile format with file sizes
		const zips: ZipFile[] = await Promise.all(
			files.map(async (filePath) => {
				let size: number | undefined;
				try {
					const stats = await stat(filePath);
					size = stats.size;
				} catch {
					// Ignore stat errors
				}
				return {
					name: basename(filePath),
					fullPath: filePath,
					parentDir: dirname(filePath),
					size,
				};
			})
		);

		return { zips };
	} catch (err) {
		return {
			zips: [],
			error: err instanceof Error ? err.message : "Scan failed",
		};
	}
}

// ============================================================================
// Directory Tree Builder
// ============================================================================

/**
 * Builds a set of all directories that contain ZIPs (at any depth)
 */
export function buildDirsWithZips(zips: ZipFile[], rootPath: string): Set<string> {
	const dirs = new Set<string>();
	// Ensure path ends with separator but don't double it (handles root "/" correctly)
	const rootWithSep = rootPath.endsWith(sep) ? rootPath : rootPath + sep;

	for (const zip of zips) {
		let dir = zip.parentDir;
		// Check if dir is under rootPath (exact match or starts with rootPath + separator)
		while ((dir === rootPath || dir.startsWith(rootWithSep)) && dir !== rootPath) {
			dirs.add(dir);
			dir = dirname(dir);
		}
		if (dir === rootPath) {
			dirs.add(rootPath);
		}
	}

	return dirs;
}

/**
 * Gets ZIPs directly in a specific directory
 */
export function getZipsInDir(zips: ZipFile[], dirPath: string): ZipFile[] {
	return zips.filter((zip) => zip.parentDir === dirPath);
}

/**
 * Gets child directories that contain ZIPs, with counts
 */
export function getChildDirsWithZips(
	zips: ZipFile[],
	currentPath: string
): DirEntry[] {
	const childDirs = new Map<string, number>();

	for (const zip of zips) {
		// Ensure path ends with separator but don't double it (handles root "/" correctly)
		const pathWithSep = currentPath.endsWith(sep) ? currentPath : currentPath + sep;

		// Skip if not under current path (must be actual child, not just string prefix)
		if (!zip.parentDir.startsWith(pathWithSep)) continue;
		// Skip if directly in current dir
		if (zip.parentDir === currentPath) continue;

		// Get the immediate child directory (slice from the end of pathWithSep)
		const relativePath = zip.parentDir.slice(pathWithSep.length);
		const parts = relativePath.split(sep).filter(Boolean);
		if (parts.length === 0) continue;

		const childDir = parts[0];
		if (!childDir) continue;
		const fullChildPath = join(currentPath, childDir);

		childDirs.set(fullChildPath, (childDirs.get(fullChildPath) || 0) + 1);
	}

	return Array.from(childDirs.entries())
		.map(([fullPath, zipCount]) => ({
			name: basename(fullPath),
			fullPath,
			zipCount,
		}))
		.sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * Builds the full entry list for a directory view
 */
export function buildEntries(
	zips: ZipFile[],
	currentPath: string,
	rootPath: string
): Array<DirEntry | (ZipFile & { type: "zip" })> {
	const result: Array<DirEntry | (ZipFile & { type: "zip" })> = [];

	// Add parent directory if not at root
	if (currentPath !== rootPath) {
		result.push({
			name: "..",
			fullPath: dirname(currentPath),
			zipCount: 0,
			isParent: true,
		});
	}

	// Add directories that contain ZIPs
	const childDirs = getChildDirsWithZips(zips, currentPath);
	for (const dir of childDirs) {
		result.push(dir);
	}

	// Add ZIPs in current directory
	const zipsHere = getZipsInDir(zips, currentPath);
	for (const zip of zipsHere) {
		result.push({ ...zip, type: "zip" });
	}

	return result;
}
