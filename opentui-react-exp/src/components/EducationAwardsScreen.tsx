import { useKeyboard } from "@opentui/react";
import { useEffect, useState } from "react";
import { api } from "../api/endpoints";
import { useAppState } from "../context/AppContext";
import { theme } from "../types";
import { toErrorMessage } from "../utils";
import { TopBar } from "./TopBar";

interface EducationAwardsScreenProps {
	onNext: (target: string) => void;
}

interface Education {
	id: number;
	institution: string;
	degree: string;
	field_of_study?: string;
	start_date: string;
	end_date?: string;
	gpa?: string;
	honors?: string;
}

interface Award {
	id: number;
	title: string;
	issuer: string;
	date: string;
	description?: string;
}

export function EducationAwardsScreen({ onNext }: EducationAwardsScreenProps) {
	const { state } = useAppState();
	const [education, setEducation] = useState<Education[]>([]);
	const [awards, setAwards] = useState<Award[]>([]);
	const [selectedColumn, setSelectedColumn] = useState<"education" | "awards">("education");
	const [selectedIndex, setSelectedIndex] = useState(0);
	const [error, setError] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);

	// Use selectedEmail as portfolio identifier (user's unique ID from pipeline)
	const portfolioId = state.selectedEmail || "default";

	useEffect(() => {
		const loadData = async () => {
			setLoading(true);
			try {
				const [educationData, awardsData] = await Promise.all([
					api.listEducation(portfolioId),
					api.listAwards(portfolioId),
				]);
				setEducation(educationData || []);
				setAwards(awardsData || []);
				setError(null);
			} catch (err) {
				setError(toErrorMessage(err));
			} finally {
				setLoading(false);
			}
		};
		void loadData();
	}, [portfolioId]);

	const handleDeleteEducation = async (id: number) => {
		try {
			await api.deleteEducation(id);
			setEducation((prev) => prev.filter((e) => e.id !== id));
		} catch (err) {
			setError(toErrorMessage(err));
		}
	};

	const handleDeleteAward = async (id: number) => {
		try {
			await api.deleteAward(id);
			setAwards((prev) => prev.filter((a) => a.id !== id));
		} catch (err) {
			setError(toErrorMessage(err));
		}
	};

	useKeyboard((key) => {
		if (key.name === "left" || key.name === "right") {
			setSelectedColumn((prev) => (prev === "education" ? "awards" : "education"));
			setSelectedIndex(0);
			return;
		}

		if (key.name === "up") {
			setSelectedIndex((prev) => Math.max(0, prev - 1));
			return;
		}

		if (key.name === "down") {
			const max = selectedColumn === "education" ? education.length : awards.length;
			setSelectedIndex((prev) => Math.min(max - 1, prev + 1));
			return;
		}

		if (key.name === "delete" || (key.name === "d" && key.ctrl)) {
			if (selectedColumn === "education" && education[selectedIndex]) {
				void handleDeleteEducation(education[selectedIndex].id);
			} else if (selectedColumn === "awards" && awards[selectedIndex]) {
				void handleDeleteAward(awards[selectedIndex].id);
			}
			return;
		}

		if (key.name === "return") {
			onNext("file-upload");
			return;
		}

		if (key.name === "escape") {
			onNext("project-list");
		}
	});

	const educationLines = education.map((e, i) => {
		const highlight = selectedColumn === "education" && selectedIndex === i;
		const prefix = highlight ? "▶ " : "  ";
		return `${prefix}${e.institution} - ${e.degree} (${e.start_date})`;
	});

	const awardLines = awards.map((a, i) => {
		const highlight = selectedColumn === "awards" && selectedIndex === i;
		const prefix = highlight ? "▶ " : "  ";
		return `${prefix}${a.title} - ${a.issuer} (${a.date})`;
	});

	const educationDetails = education[selectedIndex];
	const awardDetails = awards[selectedIndex];

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				title="Education & Awards"
				description="Manage your education and awards"
			/>

			{error && (
				<box padding={1} backgroundColor={theme.error}>
					<text>
						<span fg={theme.textPrimary}>Error: {error}</span>
					</text>
				</box>
			)}

			{loading ? (
				<text>
					<span fg={theme.textSecondary}>Loading...</span>
				</text>
			) : (
				<box flexDirection="column" flexGrow={1} padding={2} gap={2}>
					<box flexDirection="row" gap={4} flexGrow={1}>
						{/* Education Column */}
						<box flexDirection="column" flexGrow={1}>
							<text>
								<span
									fg={
										selectedColumn === "education" ? theme.gold : theme.textDim
									}
								>
									<strong>EDUCATION ({education.length})</strong>
								</span>
							</text>
							<box flexDirection="column" gap={1} marginTop={1}>
								{educationLines.length > 0 ? (
									educationLines.map((line, i) => (
										<text key={i}>
											<span fg={theme.textSecondary}>{line}</span>
										</text>
									))
								) : (
									<text>
										<span fg={theme.textDim}>No education entries</span>
									</text>
								)}
							</box>

							{educationDetails && (
								<box
									flexDirection="column"
									gap={1}
									marginTop={2}
									paddingTop={1}
									border
									borderColor={theme.textDim}
								>
									<text>
										<span fg={theme.cyan}>
											Field: {educationDetails.field_of_study || "N/A"}
										</span>
									</text>
									<text>
										<span fg={theme.cyan}>
											GPA: {educationDetails.gpa || "N/A"}
										</span>
									</text>
									<text>
										<span fg={theme.cyan}>
											Honors: {educationDetails.honors || "N/A"}
										</span>
									</text>
									{educationDetails.end_date && (
										<text>
											<span fg={theme.cyan}>
												End: {educationDetails.end_date}
											</span>
										</text>
									)}
								</box>
							)}
						</box>

						{/* Awards Column */}
						<box flexDirection="column" flexGrow={1}>
							<text>
								<span
									fg={selectedColumn === "awards" ? theme.gold : theme.textDim}
								>
									<strong>AWARDS ({awards.length})</strong>
								</span>
							</text>
							<box flexDirection="column" gap={1} marginTop={1}>
								{awardLines.length > 0 ? (
									awardLines.map((line, i) => (
										<text key={i}>
											<span fg={theme.textSecondary}>{line}</span>
										</text>
									))
								) : (
									<text>
										<span fg={theme.textDim}>No awards</span>
									</text>
								)}
							</box>

							{awardDetails && (
								<box
									flexDirection="column"
									gap={1}
									marginTop={2}
									paddingTop={1}
									border
									borderColor={theme.textDim}
								>
									<text>
										<span fg={theme.cyan}>Description:</span>
									</text>
									<text>
										<span fg={theme.cyan}>
											{awardDetails.description || "N/A"}
										</span>
									</text>
								</box>
							)}
						</box>
					</box>

					<box border borderColor={theme.textDim} paddingTop={1}>
						<text>
							<span fg={theme.textDim}>
								↑↓ Navigate | ← → Switch Column | Delete to remove | Enter to
								continue
							</span>
						</text>
					</box>
				</box>
			)}
		</box>
	);
}
