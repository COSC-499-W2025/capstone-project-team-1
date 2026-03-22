import { useEffect, useState } from "react";
import { useKeyboard } from "@opentui/react";
import { api } from "../api/endpoints";
import type { ConsentLevel } from "../api/types";
import { theme } from "../types";
import { TopBar } from "./TopBar";

interface ConsentScreenProps {
	onContinue: () => void;
	onBack: () => void;
}

const OPTIONS: ConsentLevel[] = ["local", "local-llm", "cloud"];

// ── ConsentPanel ──────────────────────────────────────────────────────────────

interface SectionItem {
	text: string;
	color?: string;
}

interface Section {
	heading: string;
	headingColor: string;
	items: SectionItem[];
}

interface RatingItem {
	text: string;
	color: string;
}

interface ConsentPanelProps {
	level: ConsentLevel;
	selected: ConsentLevel;
	title: string;
	subtitle: string;
	description: string;
	sections: Section[];
	ratings: RatingItem[];
	onSelect: () => void;
}

function ConsentPanel({
	level,
	selected,
	title,
	subtitle,
	description,
	sections,
	ratings,
	onSelect,
}: ConsentPanelProps) {
	const isSelected = selected === level;
	const borderColor = isSelected ? theme.gold : theme.textDim;
	const bgColor = isSelected ? theme.bgMedium : theme.bgDark;
	const titleColor = isSelected ? theme.gold : theme.textSecondary;

	return (
		<box
			flexGrow={1}
			flexDirection="column"
			padding={2}
			border
			borderStyle="rounded"
			borderColor={borderColor}
			backgroundColor={bgColor}
			gap={1}
			onMouseDown={onSelect}
		>
			<text>
				<span fg={titleColor}>
					<strong>{title}</strong>
				</span>
				<span fg={theme.textDim}>  · {subtitle}</span>
			</text>

			<text>
				<span fg={theme.textDim}>{description}</span>
			</text>

			{sections.map((section, i) => (
				<box key={i} flexDirection="column">
					<text>
						<span fg={section.headingColor}>
							<strong>{section.heading}</strong>
						</span>
					</text>
					{section.items.map((item, j) => (
						<text key={j}>
							<span fg={item.color ?? theme.textSecondary}>{item.text}</span>
						</text>
					))}
				</box>
			))}

			<box flexDirection="column">
				{ratings.map((item, i) => (
					<text key={i}>
						<span fg={item.color}>{item.text}</span>
					</text>
				))}
			</box>
		</box>
	);
}

// ── Panel data ────────────────────────────────────────────────────────────────

type PanelConfig = Omit<ConsentPanelProps, "selected">;

const PANELS: PanelConfig[] = [
	{
		level: "local",
		title: "Local Only",
		subtitle: "pattern-based",
		description: "Reads your repos using static rules. No AI model needed or involved.",
		sections: [
			{
				heading: "What we read",
				headingColor: theme.cyan,
				items: [
					{ text: "· File & folder names" },
					{ text: "· Language detection" },
					{ text: "· Commit count & dates" },
					{ text: "· Framework fingerprints" },
				],
			},
			{
				heading: "Privacy",
				headingColor: theme.gold,
				items: [
					{ text: "No model required." },
					{ text: "Zero network calls." },
					{ text: "Nothing ever leaves your machine.", color: theme.textDim },
				],
			},
		],
		ratings: [
			{ text: " + Complete privacy", color: theme.success },
			{ text: " + No setup required", color: theme.success },
			{ text: " + Works instantly", color: theme.success },
			{ text: " - No AI narratives", color: theme.warning },
			{ text: " - Basic skill detection", color: theme.warning },
		],
	},
	{
		level: "local-llm",
		title: "Local AI",
		subtitle: "recommended",
		description: "Static analysis plus a small model that runs entirely on your device.",
		sections: [
			{
				heading: "What we read",
				headingColor: theme.cyan,
				items: [
					{ text: "· README files (up to 2,000 chars)" },
					{ text: "· Your commit messages" },
					{ text: "· Folder structure & file names" },
					{ text: "· Code metrics & skill timeline" },
				],
			},
			{
				heading: "What the AI sees",
				headingColor: theme.gold,
				items: [
					{ text: "Summaries & metrics only —" },
					{ text: "never your raw source code." },
					{ text: "Commit messages only reach the AI", color: theme.textDim },
					{ text: "if our classifier can't label them.", color: theme.textDim },
				],
			},
			{
				heading: "Where it runs",
				headingColor: theme.gold,
				items: [
					{ text: "A local model on your machine." },
					{ text: "No cloud. Nothing leaves here." },
					{ text: "~/.artifactminer/models/", color: theme.textDim },
				],
			},
		],
		ratings: [
			{ text: " + Rich AI-generated narratives", color: theme.success },
			{ text: " + Smart skill inference", color: theme.success },
			{ text: " + Stays fully on-device", color: theme.success },
			{ text: " - ~2 GB model download", color: theme.warning },
			{ text: " - Needs available RAM", color: theme.warning },
		],
	},
	{
		level: "cloud",
		title: "Cloud AI",
		subtitle: "coming soon",
		description: "Static analysis plus a cloud model. Best quality, no local storage needed.",
		sections: [
			{
				heading: "What gets sent",
				headingColor: theme.cyan,
				items: [
					{ text: "· File & technology names" },
					{ text: "· Commit messages" },
					{ text: "· Summaries & metrics" },
					{ text: "Sent to an external AI service.", color: theme.textDim },
				],
			},
			{
				heading: "Privacy",
				headingColor: theme.gold,
				items: [
					{ text: "Metadata leaves your device." },
					{ text: "Subject to provider's data policy." },
					{ text: "Raw source code is never sent.", color: theme.textDim },
				],
			},
		],
		ratings: [
			{ text: " + Best quality results", color: theme.success },
			{ text: " + No local setup or storage", color: theme.success },
			{ text: " ~ Not yet available", color: theme.warning },
			{ text: " - Requires network", color: theme.warning },
			{ text: " - Data leaves device", color: theme.warning },
		],
	},
];

// ── ConsentScreen ─────────────────────────────────────────────────────────────

export function ConsentScreen({ onContinue, onBack }: ConsentScreenProps) {
	const [selected, setSelected] = useState<ConsentLevel>("local-llm");
	const [saving, setSaving] = useState(false);

	const handleConfirm = () => {
		if (saving) return;
		setSaving(true);
		api.updateConsent(selected).then(() => {
			onContinue();
		}).catch(() => {
			setSaving(false);
		});
	};

	useEffect(() => {
		let ignore = false;
		api.getConsent().then((resp) => {
			if (!ignore && resp.consent_level !== "none") {
				setSelected(resp.consent_level);
			}
		}).catch((err) => { console.error("Failed to load consent:", err); });
		return () => { ignore = true; };
	}, []);

	useKeyboard((key) => {
		if (saving) return;

		if (key.name === "left") {
			setSelected((prev) => {
				const idx = OPTIONS.indexOf(prev);
				return OPTIONS[Math.max(0, idx - 1)];
			});
		}
		if (key.name === "right") {
			setSelected((prev) => {
				const idx = OPTIONS.indexOf(prev);
				return OPTIONS[Math.min(OPTIONS.length - 1, idx + 1)];
			});
		}
		if (key.name === "return") {
			handleConfirm();
		}
		if (key.name === "escape") {
			onBack();
		}
	});

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				title="Consent"
				description="Before we analyze your projects, please choose how you'd like your data to be processed. Each option below offers a different balance of privacy and quality. Your source code never leaves your machine regardless of which option you choose."
			/>

			<box
				flexGrow={1}
				flexDirection="row"
				gap={1}
				paddingTop={1}
				paddingLeft={2}
				paddingRight={2}
				paddingBottom={1}
			>
				{PANELS.map((panel) => (
					<ConsentPanel
						key={panel.level}
						{...panel}
						selected={selected}
						onSelect={() => setSelected(panel.level)}
					/>
				))}
			</box>

			{/* Confirm button */}
			<box flexDirection="row" justifyContent="center">
				<box
					border
					borderStyle="rounded"
					borderColor={saving ? theme.textDim : theme.gold}
					backgroundColor={saving ? theme.bgDark : "#1a1a00"}
					paddingLeft={2}
					paddingRight={2}
					onMouseDown={handleConfirm}
				>
					<text>
						<span fg={saving ? theme.textDim : theme.gold}>
							<strong>{saving ? "Saving..." : "Confirm"}</strong>
						</span>
					</text>
				</box>
			</box>
		</box>
	);
}
