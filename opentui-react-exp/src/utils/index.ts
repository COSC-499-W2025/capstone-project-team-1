// ZIP Scanner
export {
	scanForZips,
	buildDirsWithZips,
	getZipsInDir,
	getChildDirsWithZips,
	buildEntries,
	DEFAULT_EXCLUDE_DIRS,
	type ZipFile,
	type DirEntry,
	type ScanOptions,
	type ScanResult,
} from "./zipScanner";

// Search & Filter
export {
	createSearchIndex,
	filterEntries,
	getMatchCount,
	type SearchableEntry,
	type SearchOptions,
} from "./searchFilter";

// Path Helpers
export {
	pathToBreadcrumbs,
	formatSize,
	shortenPath,
	getParentPath,
	isAtOrAboveRoot,
} from "./pathHelpers";
