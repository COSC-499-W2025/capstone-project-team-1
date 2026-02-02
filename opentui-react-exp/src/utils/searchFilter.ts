import Fuse from "fuse.js";
import type { ZipFile, DirEntry } from "./zipScanner";

// ============================================================================
// Types
// ============================================================================

export type SearchableEntry = DirEntry | (ZipFile & { type: "zip" });

export type SearchOptions = {
	threshold?: number; // 0 = exact, 1 = match anything (default: 0.4)
	keys?: string[];    // Fields to search (default: ["name", "fullPath"])
};

// ============================================================================
// Search/Filter
// ============================================================================

/**
 * Creates a Fuse.js instance for fuzzy searching entries
 */
export function createSearchIndex(
	entries: SearchableEntry[],
	options: SearchOptions = {}
): Fuse<SearchableEntry> {
	const { threshold = 0.4, keys = ["name", "fullPath"] } = options;

	return new Fuse(entries, {
		keys,
		threshold,
		includeScore: true,
	});
}

/**
 * Filters entries based on search query
 * Returns all entries if query is empty
 */
export function filterEntries(
	entries: SearchableEntry[],
	query: string,
	options: SearchOptions = {}
): SearchableEntry[] {
	if (!query.trim()) {
		return entries;
	}

	const fuse = createSearchIndex(
		entries.filter((e) => !("isParent" in e && e.isParent)),
		options
	);

	const results = fuse.search(query);
	const parentEntry = entries.find((e) => "isParent" in e && e.isParent);
	const filtered = results.map((r) => r.item);

	// Always keep parent entry at top when searching
	return parentEntry ? [parentEntry, ...filtered] : filtered;
}

/**
 * Gets the count of non-parent entries in a list
 */
export function getMatchCount(entries: SearchableEntry[]): number {
	return entries.filter((e) => !("isParent" in e && e.isParent)).length;
}
