import { useCallback, useState } from "react";
import { useKeyboard } from "@opentui/react";
import type {
	DeveloperProfile,
	HiddenStrength,
	Impact,
	ProjectCard,
	TalkingPoint,
} from "../api/types";
import { theme } from "../types";
import { TopBar } from "./TopBar";

// ── Tab definitions ──────────────────────────────────────────────

type Tab = "resume" | "insights" | "projects";

const TABS: Array<{ name: string; description: string; value: Tab }> = [
	{ name: "Insights", description: "Developer DNA, strengths, and impact", value: "insights" },
	{ name: "Projects", description: "Project-by-project skill cards", value: "projects" },
	{ name: "Resume", description: "Your generated resume", value: "resume" },
];

// ── Props ────────────────────────────────────────────────────────

interface CloudResumePreviewProps {
	profile: DeveloperProfile;
	onBack: () => void;
	onRestart: () => void;
}

// ── Inline markdown renderer ─────────────────────────────────────

interface MdBlock {
	type: "h1" | "h2" | "h3" | "paragraph" | "bullet" | "blank";
	text: string;
}

function parseMarkdown(raw: string): MdBlock[] {
	const blocks: MdBlock[] = [];
	for (const line of raw.split("\n")) {
		if (line.startsWith("### ")) {
			blocks.push({ type: "h3", text: line.slice(4) });
		} else if (line.startsWith("## ")) {
			blocks.push({ type: "h2", text: line.slice(3) });
		} else if (line.startsWith("# ")) {
			blocks.push({ type: "h1", text: line.slice(2) });
		} else if (line.startsWith("- ")) {
			blocks.push({ type: "bullet", text: line.slice(2) });
		} else if (line.trim() === "") {
			blocks.push({ type: "blank", text: "" });
		} else {
			blocks.push({ type: "paragraph", text: line });
		}
	}
	return blocks;
}

function InlineText({ text }: { text: string }) {
	const parts: JSX.Element[] = [];
	const pattern = /\*\*(.+?)\*\*|`(.+?)`/g;
	let last = 0;
	let match: RegExpExecArray | null;

	while ((match = pattern.exec(text)) !== null) {
		if (match.index > last) {
			parts.push(
				<span key={`t${last}`} fg={theme.textSecondary}>
					{text.slice(last, match.index)}
				</span>,
			);
		}
		if (match[1] !== undefined) {
			parts.push(
				<span key={`b${match.index}`} fg={theme.textPrimary}>
					<strong>{match[1]}</strong>
				</span>,
			);
		} else if (match[2] !== undefined) {
			parts.push(
				<span key={`c${match.index}`} fg={theme.gold}>
					{match[2]}
				</span>,
			);
		}
		last = match.index + match[0].length;
	}
	if (last < text.length) {
		parts.push(
			<span key={`t${last}`} fg={theme.textSecondary}>
				{text.slice(last)}
			</span>,
		);
	}

	return <text>{parts}</text>;
}

// ── Resume tab ───────────────────────────────────────────────────

function ResumeTab({ markdown }: { markdown: string }) {
	const blocks = parseMarkdown(markdown);
	return (
		<box flexDirection="column" gap={0}>
			{blocks.map((block, i) => {
				switch (block.type) {
					case "h1":
						return (
							<box key={i} paddingBottom={1}>
								<text>
									<span fg={theme.gold}>
										<strong>{block.text}</strong>
									</span>
								</text>
							</box>
						);
					case "h2":
						return (
							<box key={i} paddingTop={1}>
								<text>
									<span fg={theme.cyan}>
										<strong>{block.text}</strong>
									</span>
								</text>
							</box>
						);
					case "h3":
						return (
							<box key={i} paddingTop={1}>
								<text>
									<span fg={theme.cyan}>{block.text}</span>
								</text>
							</box>
						);
					case "bullet":
						return (
							<box key={i} paddingLeft={2} flexDirection="row">
								<text>
									<span fg={theme.textDim}>{"• "}</span>
								</text>
								<InlineText text={block.text} />
							</box>
						);
					case "blank":
						return <box key={i} height={1} />;
					case "paragraph":
						return (
							<box key={i}>
								<InlineText text={block.text} />
							</box>
						);
				}
			})}
		</box>
	);
}

// ── Insights tab ─────────────────────────────────────────────────

function DNACard({ dna }: { dna: DeveloperProfile["developer_dna"] }) {
	return (
		<box
			flexDirection="column"
			border
			borderStyle="rounded"
			borderColor={theme.gold}
			paddingLeft={2}
			paddingRight={2}
			paddingTop={1}
			paddingBottom={1}
		>
			<text>
				<span fg={theme.gold}>
					<strong>{dna.archetype}</strong>
				</span>
			</text>
			<box height={1} />
			<text>
				<span fg={theme.textSecondary}>{dna.description}</span>
			</text>
			{dna.defining_traits.length > 0 && (
				<box flexDirection="column" marginTop={1}>
					{dna.defining_traits.map((trait, i) => (
						<text key={i}>
							<span fg={theme.cyan}>{"  \u25cf "}</span>
							<span fg={theme.textSecondary}>{trait}</span>
						</text>
					))}
				</box>
			)}
		</box>
	);
}

function HiddenStrengthsSection({ strengths }: { strengths: HiddenStrength[] }) {
	if (strengths.length === 0) return null;
	return (
		<box flexDirection="column" marginTop={2}>
			<text>
				<span fg={theme.gold}>
					<strong>Hidden Strengths</strong>
				</span>
			</text>
			<box height={1} />
			{strengths.map((s, i) => (
				<box key={i} flexDirection="column" marginBottom={1} paddingLeft={1}>
					<text>
						<span fg={theme.cyan}>{"\u25cf "}</span>
						<span fg={theme.textPrimary}>
							<strong>{s.observation}</strong>
						</span>
					</text>
					<box paddingLeft={2}>
						<text>
							<span fg={theme.textSecondary}>{s.evidence}</span>
						</text>
					</box>
					<box paddingLeft={2}>
						<text>
							<span fg={theme.textDim}>
								<em>{s.why_it_matters}</em>
							</span>
						</text>
					</box>
				</box>
			))}
		</box>
	);
}

function TalkingPointsSection({ points }: { points: TalkingPoint[] }) {
	if (points.length === 0) return null;
	return (
		<box flexDirection="column" marginTop={2}>
			<text>
				<span fg={theme.gold}>
					<strong>Interview Talking Points</strong>
				</span>
			</text>
			<box height={1} />
			{points.map((p, i) => (
				<box key={i} flexDirection="column" marginBottom={1} paddingLeft={1}>
					<text>
						<span fg={theme.cyan}>{"\u25b8 "}</span>
						<span fg={theme.textPrimary}>
							<strong>{p.topic}</strong>
						</span>
					</text>
					<box paddingLeft={2}>
						<text>
							<span fg={theme.textDim}>{`"${p.story}"`}</span>
						</text>
					</box>
				</box>
			))}
		</box>
	);
}

function ImpactSection({ impact }: { impact: Impact }) {
	return (
		<box flexDirection="column" marginTop={2}>
			<text>
				<span fg={theme.gold}>
					<strong>Impact</strong>
				</span>
			</text>
			<box height={1} />

			{/* Commits */}
			{impact.commits.total > 0 && (
				<box flexDirection="column" paddingLeft={1} marginBottom={1}>
					<text>
						<span fg={theme.cyan}>Commits </span>
						<span fg={theme.textPrimary}>
							<strong>{String(impact.commits.total)}</strong>
						</span>
						<span fg={theme.textDim}>
							{` total, ~${String(impact.commits.avg_per_week)}/week`}
						</span>
					</text>
					{impact.commits.most_active_period ? (
						<text>
							<span fg={theme.textDim}>
								{`  Most active: ${impact.commits.most_active_period}`}
							</span>
						</text>
					) : null}
					{impact.commits.conventional_commits_pct > 0 ? (
						<text>
							<span fg={theme.textDim}>
								{`  Conventional commits: ${String(impact.commits.conventional_commits_pct)}%`}
							</span>
						</text>
					) : null}
				</box>
			)}

			{/* Languages */}
			{impact.languages.length > 0 && (
				<box flexDirection="column" paddingLeft={1} marginBottom={1}>
					<text>
						<span fg={theme.cyan}>Languages</span>
					</text>
					{impact.languages.map((lang, i) => (
						<text key={i}>
							<span fg={theme.textPrimary}>{`  ${lang.name}`}</span>
							<span fg={theme.textDim}>
								{` \u2014 ${String(lang.file_count)} files in ${lang.projects.join(", ")}`}
							</span>
						</text>
					))}
				</box>
			)}

			{/* Collaboration */}
			{impact.collaboration.workflow_style && (
				<box flexDirection="column" paddingLeft={1} marginBottom={1}>
					<text>
						<span fg={theme.cyan}>Workflow </span>
						<span fg={theme.textSecondary}>{impact.collaboration.workflow_style}</span>
					</text>
					{impact.collaboration.branch_count > 0 ? (
						<text>
							<span fg={theme.textDim}>
								{`  ${String(impact.collaboration.branch_count)} branches, merges ${impact.collaboration.merge_frequency}`}
							</span>
						</text>
					) : null}
				</box>
			)}

			{/* Complexity */}
			{(impact.complexity.project_types.length > 0 || impact.complexity.distinct_tools.length > 0) && (
				<box flexDirection="column" paddingLeft={1}>
					<text>
						<span fg={theme.cyan}>Breadth </span>
						<span fg={theme.textSecondary}>
							{`${String(impact.complexity.frameworks_used)} frameworks, ${String(impact.complexity.project_types.length)} project types`}
						</span>
					</text>
					{impact.complexity.project_types.length > 0 ? (
						<text>
							<span fg={theme.textDim}>
								{`  Types: ${impact.complexity.project_types.join(", ")}`}
							</span>
						</text>
					) : null}
					{impact.complexity.distinct_tools.length > 0 ? (
						<text>
							<span fg={theme.textDim}>
								{`  Tools: ${impact.complexity.distinct_tools.join(", ")}`}
							</span>
						</text>
					) : null}
				</box>
			)}
		</box>
	);
}

function InsightsTab({ profile }: { profile: DeveloperProfile }) {
	return (
		<box flexDirection="column">
			<DNACard dna={profile.developer_dna} />
			<HiddenStrengthsSection strengths={profile.hidden_strengths} />
			<TalkingPointsSection points={profile.talking_points} />
			<ImpactSection impact={profile.impact} />
		</box>
	);
}

// ── Projects tab ─────────────────────────────────────────────────

function ProjectCardView({ project }: { project: ProjectCard }) {
	return (
		<box
			flexDirection="column"
			border
			borderStyle="rounded"
			borderColor={theme.goldDim}
			paddingLeft={2}
			paddingRight={2}
			paddingTop={1}
			paddingBottom={1}
			marginBottom={1}
			title={` ${project.name} `}
			titleAlignment="left"
		>
			<text>
				<span fg={theme.textSecondary}>{project.what_it_says_about_you}</span>
			</text>

			{project.skills.length > 0 && (
				<box flexDirection="column" marginTop={1}>
					<text>
						<span fg={theme.textDim}>Skills demonstrated:</span>
					</text>
					{project.skills.map((s, i) => (
						<text key={i}>
							<span fg={theme.cyan}>{`  \u25b8 ${s.skill}`}</span>
							<span fg={theme.textDim}>{` \u2014 ${s.evidence}`}</span>
						</text>
					))}
				</box>
			)}

			{project.standout && (
				<box marginTop={1}>
					<text>
						<span fg={theme.gold}>{"\u2605 Standout: "}</span>
						<span fg={theme.textSecondary}>{project.standout}</span>
					</text>
				</box>
			)}
		</box>
	);
}

function ProjectsTab({ projects }: { projects: ProjectCard[] }) {
	if (projects.length === 0) {
		return (
			<text>
				<span fg={theme.textDim}>No project data available.</span>
			</text>
		);
	}
	return (
		<box flexDirection="column">
			{projects.map((p, i) => (
				<ProjectCardView key={i} project={p} />
			))}
		</box>
	);
}

// ── Main component ───────────────────────────────────────────────

export function CloudResumePreview({
	profile,
	onBack,
	onRestart,
}: CloudResumePreviewProps) {
	const [activeTab, setActiveTab] = useState<Tab>("insights");

	const TAB_KEYS: Record<string, Tab> = { "1": "insights", "2": "projects", "3": "resume" };

	useKeyboard(
		useCallback((key: { name: string }) => {
			const tab = TAB_KEYS[key.name];
			if (tab) setActiveTab(tab);
		}, []),
	);

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				title="Developer Profile"
				description="Your AI-generated developer profile — switch tabs to explore your resume, insights, and project analysis."
			/>

			{/* Tab bar */}
			<tab-select
				focused
				options={TABS}
				onChange={(_idx: number, opt: { value?: Tab } | null) => {
					if (opt?.value) setActiveTab(opt.value);
				}}
				showUnderline
				showDescription={false}
				backgroundColor={theme.bgDark}
				textColor={theme.textDim}
				focusedTextColor={theme.gold}
				selectedTextColor={theme.gold}
				focusedBackgroundColor={theme.bgMedium}
				selectedBackgroundColor={theme.bgDark}
			/>

			{/* Tab content */}
			<scrollbox
				flexGrow={1}
				style={{
					rootOptions: { backgroundColor: theme.bgDark },
					wrapperOptions: { flexGrow: 1 },
					viewportOptions: { padding: 2 },
				}}
			>
				{activeTab === "resume" && <ResumeTab markdown={profile.resume_markdown} />}
				{activeTab === "insights" && <InsightsTab profile={profile} />}
				{activeTab === "projects" && <ProjectsTab projects={profile.projects} />}
			</scrollbox>
		</box>
	);
}
