/**
 * Arcade-style terminal Snake game.
 *
 * Arrow keys / WASD to steer. Grid auto-sizes to the container.
 * Game over shows a big red splash screen until user presses a key.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useKeyboard } from "@opentui/react";
import { theme } from "../../types";

type Pos = { x: number; y: number };
type Dir = "up" | "down" | "left" | "right";

interface SnakeGameProps {
	width?: number;
	height?: number;
	tickMs?: number;
	onScore?: (score: number) => void;
}

const OPPOSITE: Record<Dir, Dir> = { up: "down", down: "up", left: "right", right: "left" };
const DIR_KEYS: Record<string, Dir> = {
	up: "up", w: "up",
	down: "down", s: "down",
	left: "left", a: "left",
	right: "right", d: "right",
};
const RESTART_KEYS = new Set(["up", "down", "left", "right", "w", "a", "s", "d", "space", "return"]);

const CELL_W = 4;
const CELL_H = 2;

function randomFood(w: number, h: number, occupied: Set<string>): Pos {
	let p: Pos;
	do {
		p = { x: Math.floor(Math.random() * w), y: Math.floor(Math.random() * h) };
	} while (occupied.has(`${p.x},${p.y}`));
	return p;
}

function makeOccupiedSet(snake: Pos[]): Set<string> {
	return new Set(snake.map((p) => `${p.x},${p.y}`));
}

export function SnakeGame({
	width: W = 20,
	height: H = 12,
	tickMs = 130,
	onScore,
}: SnakeGameProps) {
	const cx = Math.floor(W / 2);
	const cy = Math.floor(H / 2);
	const makeInitSnake = useCallback((): Pos[] => [
		{ x: cx, y: cy },
		{ x: cx - 1, y: cy },
		{ x: cx - 2, y: cy },
		{ x: cx - 3, y: cy },
		{ x: cx - 4, y: cy },
	], [cx, cy]);

	const [snake, setSnake] = useState<Pos[]>(makeInitSnake);
	const [food, setFood] = useState<Pos>(() => randomFood(W, H, makeOccupiedSet(makeInitSnake())));
	const [dir, setDir] = useState<Dir>("right");
	const [score, setScore] = useState(0);
	const [gameOver, setGameOver] = useState(false);

	const dirRef = useRef(dir);
	dirRef.current = dir;
	const snakeRef = useRef(snake);
	snakeRef.current = snake;
	const foodRef = useRef(food);
	foodRef.current = food;
	const scoreRef = useRef(score);
	scoreRef.current = score;
	const onScoreRef = useRef(onScore);
	onScoreRef.current = onScore;

	// Single keyboard handler for both gameplay and restart
	useKeyboard(
		useCallback((key: { name: string }) => {
			if (gameOver) {
				if (RESTART_KEYS.has(key.name)) {
					const s = makeInitSnake();
					setSnake(s);
					snakeRef.current = s;
					setDir("right");
					dirRef.current = "right";
					const f = randomFood(W, H, makeOccupiedSet(s));
					setFood(f);
					foodRef.current = f;
					setScore(0);
					scoreRef.current = 0;
					setGameOver(false);
					onScoreRef.current?.(0);
				}
				return;
			}
			const next = DIR_KEYS[key.name];
			if (next && next !== OPPOSITE[dirRef.current]) {
				setDir(next);
				dirRef.current = next;
			}
		}, [gameOver, makeInitSnake, W, H]),
	);

	// Game tick — no `score` dependency, reads from ref
	useEffect(() => {
		if (gameOver) return;

		const id = setInterval(() => {
			const s = snakeRef.current;
			const d = dirRef.current;
			const f = foodRef.current;
			const head = s[0];

			const next: Pos = {
				x: d === "left" ? head.x - 1 : d === "right" ? head.x + 1 : head.x,
				y: d === "up" ? head.y - 1 : d === "down" ? head.y + 1 : head.y,
			};

			if (next.x < 0) next.x = W - 1;
			if (next.x >= W) next.x = 0;
			if (next.y < 0) next.y = H - 1;
			if (next.y >= H) next.y = 0;

			const nextKey = `${next.x},${next.y}`;
			if (s.some((p) => `${p.x},${p.y}` === nextKey)) {
				setGameOver(true);
				return;
			}

			const ate = next.x === f.x && next.y === f.y;
			const newSnake = [next, ...s.slice(0, ate ? s.length : s.length - 1)];

			setSnake(newSnake);
			snakeRef.current = newSnake;

			if (ate) {
				const occupied = makeOccupiedSet(newSnake);
				const newFood = randomFood(W, H, occupied);
				setFood(newFood);
				foodRef.current = newFood;
				const newScore = scoreRef.current + 10;
				setScore(newScore);
				scoreRef.current = newScore;
				onScoreRef.current?.(newScore);
			}
		}, tickMs);

		return () => clearInterval(id);
	}, [gameOver, tickMs, W, H]);

	// Build occupied set once for rendering
	const occupiedMap = useMemo(() => {
		const map = new Map<string, "head" | "body">();
		for (let i = 0; i < snake.length; i++) {
			map.set(`${snake[i].x},${snake[i].y}`, i === 0 ? "head" : "body");
		}
		return map;
	}, [snake]);

	const FILL = "█".repeat(CELL_W);
	const BODY_FILL = "░".repeat(CELL_W);
	const EMPTY = " ".repeat(CELL_W);
	const DOT = " ·" + " ".repeat(CELL_W - 2);
	const foodKey = `${food.x},${food.y}`;

	// Game over splash
	if (gameOver) {
		const totalRows = H * CELL_H;
		const gameOverLines = [
			"  ▄▄▄  ▄▄▄  ▄   ▄ ▄▄▄   ",
			"  █    █   █ ██ ██ █      ",
			"  █ ▄▄ █▄▄▄█ █ █ █ █▄▄   ",
			"  █  █ █   █ █   █ █      ",
			"  ▀▀▀  ▀   ▀ ▀   ▀ ▀▀▀   ",
			"                          ",
			"  ▄▄▄  ▄   ▄ ▄▄▄ ▄▄▄  ▄  ",
			"  █  █ █   █ █   █  █ █  ",
			"  █  █  █ █  █▄▄ █▄▄▀ █  ",
			"  █  █  █ █  █   █ █     ",
			"  ▀▀▀    ▀   ▀▀▀ ▀  ▀ ▀  ",
		];
		const padTop = Math.max(0, Math.floor((totalRows - gameOverLines.length - 3) / 2));
		const gridW = W * CELL_W;

		return (
			<box
				flexDirection="column"
				flexGrow={1}
				border
				borderStyle="rounded"
				borderColor={theme.error}
				backgroundColor="#1a0000"
			>
				{Array.from({ length: padTop }, (_, i) => (
					<text key={`pad-${i}`}>{" "}</text>
				))}
				{gameOverLines.map((line, i) => (
					<text key={`go-${i}`}>
						<span fg={theme.error}>
							{line.padStart(Math.floor((gridW + line.length) / 2)).padEnd(gridW)}
						</span>
					</text>
				))}
				<text>{" "}</text>
				<text>
					<span fg={theme.gold}>
						{"Score: ".padStart(Math.floor(gridW / 2) - 2)}{score}
					</span>
				</text>
				<text>
					<span fg={theme.textDim}>
						{"Press any key to restart".padStart(Math.floor(gridW / 2) + 8)}
					</span>
				</text>
			</box>
		);
	}

	// Active game grid — uses occupiedMap for O(1) lookup per cell
	const gridRows = [];
	for (let y = 0; y < H; y++) {
		for (let row = 0; row < CELL_H; row++) {
			const cells = [];
			for (let x = 0; x < W; x++) {
				const key = `${x},${y}`;
				const cellType = occupiedMap.get(key);

				if (cellType === "head") {
					cells.push(<span key={x} fg={theme.gold}>{FILL}</span>);
				} else if (cellType === "body") {
					cells.push(<span key={x} fg={theme.goldDark}>{BODY_FILL}</span>);
				} else if (key === foodKey) {
					cells.push(<span key={x} fg={theme.error}>{FILL}</span>);
				} else {
					cells.push(<span key={x} fg="#333333">{row === 0 ? DOT : EMPTY}</span>);
				}
			}
			gridRows.push(<text key={`${y}-${row}`}>{cells}</text>);
		}
	}

	return (
		<box
			flexDirection="column"
			flexGrow={1}
			border
			borderStyle="rounded"
			borderColor={theme.goldDim}
		>
			{gridRows}
			<box flexDirection="row" justifyContent="space-between" paddingLeft={1} paddingRight={1}>
				<text>
					<span fg={theme.gold}>
						<strong>Score: {score}</strong>
					</span>
				</text>
				<text>
					<span fg={theme.textDim}>Arrow keys / WASD</span>
				</text>
			</box>
		</box>
	);
}
