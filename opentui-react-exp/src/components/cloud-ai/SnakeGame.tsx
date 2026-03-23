/**
 * Arcade-style terminal Snake game.
 *
 * Arrow keys / WASD to steer. Grid auto-sizes to the container.
 * Features: HI-SCORE tracking, speed-up on score, blinking food,
 * gradient snake body, glowing head.
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

/** Body gradient: head-adjacent segments are bright gold, tail fades to dim */
const BODY_GRADIENT = [
	"#FFD700", "#F5CC00", "#EBC200", "#E0B800",
	"#D5AE00", "#CBA400", "#C09A00", "#B59000",
	"#AA8600", "#A07C00", "#957200", "#8B7500",
];

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

/** Module-level hi-score — persists across unmount/remount within session */
let globalHiScore = 0;

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
	const [hiScore, setHiScore] = useState(globalHiScore);
	const [flash, setFlash] = useState(true);

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

	// Flash "GAME OVER" text when dead
	useEffect(() => {
		if (!gameOver) return;
		const id = setInterval(() => setFlash((v) => !v), 500);
		return () => clearInterval(id);
	}, [gameOver]);

	// Speed increases every 30 points (3 food items eaten), capped at 60ms
	const speedLevel = Math.floor(score / 30);
	const effectiveTick = Math.max(60, tickMs - speedLevel * 8);

	// Track hi-score across games
	useEffect(() => {
		if (score > globalHiScore) {
			globalHiScore = score;
			setHiScore(score);
		}
	}, [score]);

	const restart = useCallback(() => {
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
	}, [makeInitSnake, W, H]);

	// Single keyboard handler for both gameplay and restart
	useKeyboard(
		useCallback((key: { name: string }) => {
			if (gameOver) {
				if (RESTART_KEYS.has(key.name)) restart();
				return;
			}
			const next = DIR_KEYS[key.name];
			if (next && next !== OPPOSITE[dirRef.current]) {
				setDir(next);
				dirRef.current = next;
			}
		}, [gameOver, restart]),
	);

	// Game tick — uses effectiveTick so the game speeds up as score grows
	useEffect(() => {
		if (gameOver) return;

		const id = setInterval(() => {
			const s = snakeRef.current;
			const d = dirRef.current;
			const f = foodRef.current;
			const head = s[0]!;

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
		}, effectiveTick);

		return () => clearInterval(id);
	}, [gameOver, effectiveTick, W, H]);

	// Build index map — stores position in snake array for O(1) gradient lookup
	const occupiedMap = useMemo(() => {
		const map = new Map<string, number>();
		for (let i = 0; i < snake.length; i++) {
			const seg = snake[i]!;
			map.set(`${seg.x},${seg.y}`, i);
		}
		return map;
	}, [snake]);

	const FILL = "█".repeat(CELL_W);
	const SHADE_DARK = "▓".repeat(CELL_W);
	const SHADE_MED = "▒".repeat(CELL_W);
	const SHADE_LIGHT = "░".repeat(CELL_W);
	const EMPTY = " ".repeat(CELL_W);
	const foodKey = `${food.x},${food.y}`;
	const gridW = W * CELL_W;

	// Arcade-style score header — score glows on game over
	const scoreColor = gameOver ? (flash ? "#FFFF00" : theme.gold) : theme.gold;
	const scoreHeader = (
		<box flexDirection="row" justifyContent="space-between" paddingLeft={1} paddingRight={1} marginBottom={1}>
			<text>
				<span fg={scoreColor}>
					<strong>SCORE  {String(score).padStart(4, "0")}</strong>
				</span>
			</text>
			<text>
				<span fg={theme.goldDim}>
					<strong>HI-SCORE  {String(hiScore).padStart(4, "0")}</strong>
				</span>
			</text>
		</box>
	);

	// Game over splash
	if (gameOver) {
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
		return (
			<box
				flexDirection="column"
				flexGrow={1}
				border
				borderStyle="rounded"
				borderColor={theme.error}
				backgroundColor="#1a0000"
			>
				{scoreHeader}
				<box flexGrow={1} />
				<box flexDirection="column" alignItems="center">
					{gameOverLines.map((line, i) => (
						<text key={`go-${i}`}>
							<span fg={flash ? "#FF4444" : "#991111"}>
								{line}
							</span>
						</text>
					))}
					<text>{" "}</text>
					<box
						border
						borderStyle="rounded"
						borderColor={flash ? theme.gold : theme.goldDim}
						paddingLeft={3}
						paddingRight={3}
						onMouseDown={restart}
					>
						<text>
							<span fg={theme.gold}>
								<strong>PLAY AGAIN</strong>
							</span>
						</text>
					</box>
				</box>
				<box flexGrow={1} />
				<box flexDirection="row" justifyContent="center">
					<text>
						<span fg={theme.textDim}>Press any key to restart</span>
					</text>
				</box>
			</box>
		);
	}

	// Active game grid — gradient body, glowing head, blinking food
	const gridRows = [];
	for (let y = 0; y < H; y++) {
		for (let row = 0; row < CELL_H; row++) {
			const cells = [];
			for (let x = 0; x < W; x++) {
				const key = `${x},${y}`;
				const snakeIdx = occupiedMap.get(key);

				if (snakeIdx === 0) {
					// Head — brightest gold with subtle background glow
					cells.push(<span key={x} fg="#FFEE00" bg="#2a2200">{FILL}</span>);
				} else if (snakeIdx !== undefined) {
					// Body — shade chars fade from dense to sparse
					const gradIdx = Math.min(snakeIdx, BODY_GRADIENT.length - 1);
					const shade = snakeIdx <= 3 ? SHADE_DARK : snakeIdx <= 6 ? SHADE_MED : SHADE_LIGHT;
					cells.push(<span key={x} fg={BODY_GRADIENT[gradIdx]}>{shade}</span>);
				} else if (key === foodKey) {
					// Food — solid bright red
					cells.push(<span key={x} fg="#FF4444">{FILL}</span>);
				} else {
					cells.push(<span key={x}>{EMPTY}</span>);
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
			{scoreHeader}
			{gridRows}
			<box flexGrow={1} />
			<box flexDirection="row" justifyContent="center" paddingLeft={1} paddingRight={1}>
				<text>
					<span fg={theme.textDim}>Arrow keys / WASD</span>
				</text>
			</box>
		</box>
	);
}
