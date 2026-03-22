/**
 * Knight Rider-style bidirectional sweep spinner.
 *
 * Ported from anomalyco/opencode's spinner utility.
 * Generates frames + per-character color gradients for
 * the opentui-spinner <spinner> element.
 */
import type { ColorInput } from "@opentui/core";
import { RGBA } from "@opentui/core";
import type { ColorGenerator } from "opentui-spinner";

// ── Types ────────────────────────────────────────────────

interface ScannerState {
	activePosition: number;
	isHolding: boolean;
	holdProgress: number;
	holdTotal: number;
	movementProgress: number;
	movementTotal: number;
	isMovingForward: boolean;
}

interface TrailOptions {
	colors: ColorInput[];
	trailLength: number;
	defaultColor: RGBA;
	direction: "bidirectional";
	holdFrames: { start: number; end: number };
	enableFading?: boolean;
	minAlpha?: number;
}

export interface KnightRiderOptions {
	width?: number;
	style?: "blocks" | "diamonds";
	holdStart?: number;
	holdEnd?: number;
	color?: ColorInput;
	trailSteps?: number;
	inactiveFactor?: number;
	enableFading?: boolean;
	minAlpha?: number;
}

// ── Color Derivation ─────────────────────────────────────

function deriveTrailColors(brightColor: ColorInput, steps = 6): RGBA[] {
	const base =
		brightColor instanceof RGBA
			? brightColor
			: RGBA.fromHex(brightColor as string);

	return Array.from({ length: steps }, (_, i) => {
		let alpha: number;
		let bf: number;

		if (i === 0) {
			alpha = 1.0;
			bf = 1.0;
		} else if (i === 1) {
			alpha = 0.9;
			bf = 1.15; // bloom
		} else {
			alpha = Math.pow(0.65, i - 1);
			bf = 1.0;
		}

		return RGBA.fromValues(
			Math.min(1.0, base.r * bf),
			Math.min(1.0, base.g * bf),
			Math.min(1.0, base.b * bf),
			alpha,
		);
	});
}

function deriveInactiveColor(brightColor: ColorInput, factor = 0.2): RGBA {
	const base =
		brightColor instanceof RGBA
			? brightColor
			: RGBA.fromHex(brightColor as string);

	return RGBA.fromValues(base.r, base.g, base.b, factor);
}

// ── Scanner State Machine ────────────────────────────────

function getScannerState(
	frameIndex: number,
	totalChars: number,
	holdEnd: number,
	holdStart: number,
): ScannerState {
	const forwardFrames = totalChars;
	const backwardFrames = totalChars - 1;

	if (frameIndex < forwardFrames) {
		return {
			activePosition: frameIndex,
			isHolding: false,
			holdProgress: 0,
			holdTotal: 0,
			movementProgress: frameIndex,
			movementTotal: forwardFrames,
			isMovingForward: true,
		};
	}
	if (frameIndex < forwardFrames + holdEnd) {
		return {
			activePosition: totalChars - 1,
			isHolding: true,
			holdProgress: frameIndex - forwardFrames,
			holdTotal: holdEnd,
			movementProgress: 0,
			movementTotal: 0,
			isMovingForward: true,
		};
	}
	if (frameIndex < forwardFrames + holdEnd + backwardFrames) {
		const bi = frameIndex - forwardFrames - holdEnd;
		return {
			activePosition: totalChars - 2 - bi,
			isHolding: false,
			holdProgress: 0,
			holdTotal: 0,
			movementProgress: bi,
			movementTotal: backwardFrames,
			isMovingForward: false,
		};
	}
	return {
		activePosition: 0,
		isHolding: true,
		holdProgress: frameIndex - forwardFrames - holdEnd - backwardFrames,
		holdTotal: holdStart,
		movementProgress: 0,
		movementTotal: 0,
		isMovingForward: false,
	};
}

function calculateColorIndex(
	frameIndex: number,
	charIndex: number,
	totalChars: number,
	trailLength: number,
	holdEnd: number,
	holdStart: number,
	state?: ScannerState,
): number {
	const s = state ?? getScannerState(frameIndex, totalChars, holdEnd, holdStart);
	const dist = s.isMovingForward
		? s.activePosition - charIndex
		: charIndex - s.activePosition;

	if (s.isHolding) return dist + s.holdProgress;
	if (dist === 0) return 0;
	if (dist > 0 && dist < trailLength) return dist;
	return -1;
}

// ── Knight Rider Trail ColorGenerator ────────────────────

function createKnightRiderTrail(opts: TrailOptions): ColorGenerator {
	const { colors, defaultColor, enableFading = true, minAlpha = 0 } = opts;
	const baseInactiveAlpha = defaultColor.a;

	let cachedFrame = -1;
	let cachedState: ScannerState | null = null;

	return (frameIndex, charIndex, _totalFrames, totalChars) => {
		if (frameIndex !== cachedFrame) {
			cachedFrame = frameIndex;
			cachedState = getScannerState(
				frameIndex,
				totalChars,
				opts.holdFrames.end,
				opts.holdFrames.start,
			);
		}
		const state = cachedState!;
		const index = calculateColorIndex(
			frameIndex,
			charIndex,
			totalChars,
			opts.trailLength,
			opts.holdFrames.end,
			opts.holdFrames.start,
			state,
		);

		let fadeFactor = 1.0;
		if (enableFading) {
			if (state.isHolding && state.holdTotal > 0) {
				const p = Math.min(state.holdProgress / state.holdTotal, 1);
				fadeFactor = Math.max(minAlpha, 1 - p * (1 - minAlpha));
			} else if (!state.isHolding && state.movementTotal > 0) {
				const p = Math.min(
					state.movementProgress / Math.max(1, state.movementTotal - 1),
					1,
				);
				fadeFactor = minAlpha + p * (1 - minAlpha);
			}
		}

		defaultColor.a = baseInactiveAlpha * fadeFactor;

		if (index === -1) return defaultColor;
		return colors[index] ?? defaultColor;
	};
}

// ── Public API ───────────────────────────────────────────

function buildTrailOptions(options: KnightRiderOptions): TrailOptions {
	const holdStart = options.holdStart ?? 30;
	const holdEnd = options.holdEnd ?? 9;

	const colors = options.color
		? deriveTrailColors(options.color, options.trailSteps)
		: deriveTrailColors("#DAA520", 6); // gold fallback

	const defaultColor = options.color
		? deriveInactiveColor(options.color, options.inactiveFactor)
		: deriveInactiveColor("#DAA520", options.inactiveFactor ?? 0.2);

	return {
		colors,
		trailLength: colors.length,
		defaultColor,
		direction: "bidirectional",
		holdFrames: { start: holdStart, end: holdEnd },
		enableFading: options.enableFading,
		minAlpha: options.minAlpha,
	};
}

/** Generate frame strings for the Knight Rider sweep animation. */
export function createFrames(options: KnightRiderOptions = {}): string[] {
	const width = options.width ?? 8;
	const style = options.style ?? "blocks";
	const holdStart = options.holdStart ?? 30;
	const holdEnd = options.holdEnd ?? 9;

	const trailOpts = buildTrailOptions(options);
	const totalFrames = width + holdEnd + (width - 1) + holdStart;

	return Array.from({ length: totalFrames }, (_, frameIndex) => {
		return Array.from({ length: width }, (_, charIndex) => {
			const index = calculateColorIndex(
				frameIndex,
				charIndex,
				width,
				trailOpts.trailLength,
				holdEnd,
				holdStart,
			);

			if (style === "diamonds") {
				const shapes = ["⬥", "◆", "⬩", "⬪"];
				if (index >= 0 && index < trailOpts.colors.length) {
					return shapes[Math.min(index, shapes.length - 1)];
				}
				return "·";
			}

			const isActive = index >= 0 && index < trailOpts.colors.length;
			return isActive ? "■" : "⬝";
		}).join("");
	});
}

/** Generate a ColorGenerator for per-character gradient coloring. */
export function createColors(options: KnightRiderOptions = {}): ColorGenerator {
	return createKnightRiderTrail(buildTrailOptions(options));
}
