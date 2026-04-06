import { useMemo } from "react";
import type { PortfolioDashboard as PortfolioDashboardData } from "../api/types";
import { theme } from "../types";

interface PortfolioDashboardProps {
	dashboard?: PortfolioDashboardData;
}

const HEATMAP_WEEKS = 52;
const HEATMAP_ROWS = 7;

type HeatmapCell = {
	date: string;
	count: number;
};

function pad2(value: number) {
	return String(value).padStart(2, "0");
}

function toIsoDate(date: Date) {
	return `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())}`;
}

function formatYmd(value: string | null) {
	if (!value) return "n/a";
	const parsed = new Date(value);
	if (Number.isNaN(parsed.getTime())) return value;
	return parsed.toISOString().slice(0, 10);
}

function buildHeatmapGrid(
	dailyActivity: Record<string, number>,
): { rows: HeatmapCell[][]; start: string; end: string } {
	const end = new Date();
	end.setUTCHours(0, 0, 0, 0);
	const start = new Date(end);
	start.setUTCDate(start.getUTCDate() - HEATMAP_WEEKS * HEATMAP_ROWS + 1);

	const weeks: HeatmapCell[][] = Array.from({ length: HEATMAP_WEEKS }, () => []);
	for (let index = 0; index < HEATMAP_WEEKS * HEATMAP_ROWS; index += 1) {
		const day = new Date(start);
		day.setUTCDate(start.getUTCDate() + index);
		const isoDate = toIsoDate(day);
		const weekIndex = Math.floor(index / HEATMAP_ROWS);
		weeks[weekIndex]?.push({
			date: isoDate,
			count: Math.max(0, Number(dailyActivity[isoDate] ?? 0)),
		});
	}

	const rows: HeatmapCell[][] = Array.from({ length: HEATMAP_ROWS }, (_, dayIndex) =>
		weeks.map((week) => week[dayIndex] ?? { date: "", count: 0 }),
	);
	return { rows, start: toIsoDate(start), end: toIsoDate(end) };
}

function heatColor(count: number, max: number) {
	if (count <= 0 || max <= 0) return theme.textDim;
	const ratio = count / max;
	if (ratio >= 0.75) return theme.success;
	if (ratio >= 0.5) return theme.cyan;
	if (ratio >= 0.25) return theme.gold;
	return theme.goldDim;
}

function heatSymbol(count: number, max: number) {
	if (count <= 0 || max <= 0) return "·";
	const ratio = count / max;
	if (ratio >= 0.75) return "█";
	if (ratio >= 0.5) return "▓";
	if (ratio >= 0.25) return "▒";
	return "░";
}

export function PortfolioDashboard({ dashboard }: PortfolioDashboardProps) {
	const skillsTimeline = dashboard?.skills_timeline ?? [];
	const heatmap = dashboard?.activity_heatmap;
	const topProjects = dashboard?.top_projects ?? [];

	const hasTimeline = skillsTimeline.length > 0;
	const hasHeatmap = Boolean(
		heatmap && Object.keys(heatmap.daily_activity ?? {}).length > 0,
	);
	const hasTopProjects = topProjects.length > 0;
	const hasCompleteData = hasTimeline && hasHeatmap && hasTopProjects;

	const heatmapGrid = useMemo(
		() => buildHeatmapGrid(heatmap?.daily_activity ?? {}),
		[heatmap?.daily_activity],
	);
	const heatmapMax = heatmap?.max_daily_commits ?? 0;

	if (!hasCompleteData) {
		return (
			<box
				border
				borderStyle="rounded"
				borderColor={theme.warning}
				padding={2}
				title=" Portfolio Dashboard "
				titleAlignment="center"
			>
				<text>
					<span fg={theme.warning}>
						<strong>Portfolio insights unavailable for this run.</strong>
					</span>
				</text>
			</box>
		);
	}

	return (
		<box flexDirection="column" gap={1}>
			<box
				border
				borderStyle="rounded"
				borderColor={theme.goldDim}
				padding={1}
				title=" Skills Timeline "
				titleAlignment="center"
			>
				{hasTimeline ? (
					<box flexDirection="column" gap={0}>
						{skillsTimeline.map((item) => (
							<text key={item.skill}>
								<span fg={theme.gold}>
									<strong>{item.skill}</strong>
								</span>
								<span fg={theme.textDim}>
									{`  depth=${item.depth_score.toFixed(2)}  projects=${item.projects_count}  `}
								</span>
								<span fg={theme.textSecondary}>
									{`${formatYmd(item.first_seen)} → ${formatYmd(item.last_seen)}`}
								</span>
							</text>
						))}
					</box>
				) : (
					<text>
						<span fg={theme.textDim}>No skill progression data available.</span>
					</text>
				)}
			</box>

			<box
				border
				borderStyle="rounded"
				borderColor={theme.goldDim}
				padding={1}
				title=" Activity Heatmap (52 Weeks) "
				titleAlignment="center"
			>
				{hasHeatmap ? (
					<box flexDirection="column" gap={0}>
						{heatmapGrid.rows.map((row, rowIndex) => (
							<text key={`row-${rowIndex}`}>
								{row.map((cell, colIndex) => {
									const count = Number(cell.count ?? 0);
									return (
										<span
											key={`cell-${rowIndex}-${colIndex}`}
											fg={heatColor(count, heatmapMax)}
										>
											{heatSymbol(count, heatmapMax)}
										</span>
									);
								})}
							</text>
						))}
						<text>
							<span fg={theme.textDim}>
								{`${heatmapGrid.start} → ${heatmapGrid.end}  active_days=${heatmap.total_days_active}  peak=${heatmap.max_daily_commits}`}
							</span>
						</text>
					</box>
				) : (
					<text>
						<span fg={theme.textDim}>No activity heatmap data available.</span>
					</text>
				)}
			</box>

			<box
				border
				borderStyle="rounded"
				borderColor={theme.goldDim}
				padding={1}
				title=" Top Projects "
				titleAlignment="center"
			>
				{hasTopProjects ? (
					<box flexDirection="column" gap={1}>
						{topProjects.map((project, index) => (
							<box key={`${project.project_name}-${index}`} flexDirection="column">
								<text>
									<span fg={theme.gold}>
										<strong>{`${index + 1}. ${project.project_name}`}</strong>
									</span>
									<span fg={theme.textDim}>
										{`  score=${project.score.toFixed(3)}  commits=${project.commit_total}`}
									</span>
								</text>
								<text>
									<span fg={theme.textSecondary}>
										{`${formatYmd(project.first_commit)} → ${formatYmd(project.last_commit)}`}
									</span>
									{project.contribution_pct !== null ? (
										<span fg={theme.textDim}>
											{`  contribution=${project.contribution_pct.toFixed(1)}%`}
										</span>
									) : null}
								</text>
								{project.activity_focus ? (
									<text>
										<span fg={theme.cyan}>{`Activity: ${project.activity_focus}`}</span>
									</text>
								) : null}
								{project.latest_change ? (
									<text>
										<span fg={theme.textDim}>{`Latest change: ${project.latest_change}`}</span>
									</text>
								) : null}
								<text>
									<span fg={theme.textSecondary}>{project.evolution_note ?? ""}</span>
								</text>
							</box>
						))}
					</box>
				) : (
					<text>
						<span fg={theme.textDim}>No ranked project showcase data available.</span>
					</text>
				)}
			</box>
		</box>
	);
}
