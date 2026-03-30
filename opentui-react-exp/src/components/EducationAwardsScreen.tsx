import { useKeyboard } from "@opentui/react";
import { useEffect, useState } from "react";
import { api } from "../api/endpoints";
import type { Award, AwardCreateRequest, Education, EducationCreateRequest } from "../api/types";
import { useAppState } from "../context/AppContext";
import { theme } from "../types";
import { toErrorMessage } from "../utils";
import { TopBar } from "./TopBar";

interface EducationAwardsScreenProps {
	onNext: (target: string) => void;
}

type Mode = "view" | "add-education" | "add-award" | "edit-education" | "edit-award" | "confirm-delete";

interface FormState {
	// Education fields
	institution: string;
	degree: string;
	field_of_study: string;
	start_date: string;
	end_date: string;
	gpa: string;
	honors: string;
	// Award fields
	title: string;
	issuer: string;
	date: string;
	description: string;
}

const emptyForm: FormState = {
	institution: "",
	degree: "",
	field_of_study: "",
	start_date: "",
	end_date: "",
	gpa: "",
	honors: "",
	title: "",
	issuer: "",
	date: "",
	description: "",
};

const educationFields = ["institution", "degree", "field_of_study", "start_date", "end_date", "gpa", "honors"] as const;
const awardFields = ["title", "issuer", "date", "description"] as const;

export function EducationAwardsScreen({ onNext }: EducationAwardsScreenProps) {
	const { state } = useAppState();
	const [education, setEducation] = useState<Education[]>([]);
	const [awards, setAwards] = useState<Award[]>([]);
	const [selectedColumn, setSelectedColumn] = useState<"education" | "awards">("education");
	const [selectedIndex, setSelectedIndex] = useState(0);
	const [error, setError] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);
	const [mode, setMode] = useState<Mode>("view");
	const [form, setForm] = useState<FormState>(emptyForm);
	const [formFieldIndex, setFormFieldIndex] = useState(0);
	const [editingId, setEditingId] = useState<number | null>(null);

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
			await api.deleteEducation(id, portfolioId);
			setEducation((prev) => prev.filter((e) => e.id !== id));
			setSelectedIndex((prev) => Math.max(0, prev - 1));
			setMode("view");
		} catch (err) {
			setError(toErrorMessage(err));
		}
	};

	const handleDeleteAward = async (id: number) => {
		try {
			await api.deleteAward(id, portfolioId);
			setAwards((prev) => prev.filter((a) => a.id !== id));
			setSelectedIndex((prev) => Math.max(0, prev - 1));
			setMode("view");
		} catch (err) {
			setError(toErrorMessage(err));
		}
	};

	const handleCreateEducation = async () => {
		if (!form.institution || !form.degree || !form.start_date) {
			setError("Institution, degree, and start date are required");
			return;
		}
		try {
			const data: EducationCreateRequest = {
				institution: form.institution,
				degree: form.degree,
				field_of_study: form.field_of_study || null,
				start_date: form.start_date,
				end_date: form.end_date || null,
				gpa: form.gpa || null,
				honors: form.honors || null,
			};
			const created = await api.createEducation(portfolioId, data);
			setEducation((prev) => [...prev, created]);
			setForm(emptyForm);
			setMode("view");
			setError(null);
		} catch (err) {
			setError(toErrorMessage(err));
		}
	};

	const handleCreateAward = async () => {
		if (!form.title || !form.issuer || !form.date) {
			setError("Title, issuer, and date are required");
			return;
		}
		try {
			const data: AwardCreateRequest = {
				title: form.title,
				issuer: form.issuer,
				date: form.date,
				description: form.description || null,
			};
			const created = await api.createAward(portfolioId, data);
			setAwards((prev) => [...prev, created]);
			setForm(emptyForm);
			setMode("view");
			setError(null);
		} catch (err) {
			setError(toErrorMessage(err));
		}
	};

	const handleUpdateEducation = async () => {
		if (!editingId || !form.institution || !form.degree || !form.start_date) {
			setError("Institution, degree, and start date are required");
			return;
		}
		try {
			const data: EducationCreateRequest = {
				institution: form.institution,
				degree: form.degree,
				field_of_study: form.field_of_study || null,
				start_date: form.start_date,
				end_date: form.end_date || null,
				gpa: form.gpa || null,
				honors: form.honors || null,
			};
			const updated = await api.updateEducation(editingId, portfolioId, data);
			setEducation((prev) => prev.map((e) => (e.id === editingId ? updated : e)));
			setForm(emptyForm);
			setEditingId(null);
			setMode("view");
			setError(null);
		} catch (err) {
			setError(toErrorMessage(err));
		}
	};

	const handleUpdateAward = async () => {
		if (!editingId || !form.title || !form.issuer || !form.date) {
			setError("Title, issuer, and date are required");
			return;
		}
		try {
			const data: AwardCreateRequest = {
				title: form.title,
				issuer: form.issuer,
				date: form.date,
				description: form.description || null,
			};
			const updated = await api.updateAward(editingId, portfolioId, data);
			setAwards((prev) => prev.map((a) => (a.id === editingId ? updated : a)));
			setForm(emptyForm);
			setEditingId(null);
			setMode("view");
			setError(null);
		} catch (err) {
			setError(toErrorMessage(err));
		}
	};

	const startAddEducation = () => {
		setForm(emptyForm);
		setFormFieldIndex(0);
		setMode("add-education");
		setError(null);
	};

	const startAddAward = () => {
		setForm(emptyForm);
		setFormFieldIndex(0);
		setMode("add-award");
		setError(null);
	};

	const startEditEducation = (edu: Education) => {
		setForm({
			...emptyForm,
			institution: edu.institution,
			degree: edu.degree,
			field_of_study: edu.field_of_study || "",
			start_date: edu.start_date,
			end_date: edu.end_date || "",
			gpa: edu.gpa || "",
			honors: edu.honors || "",
		});
		setEditingId(edu.id);
		setFormFieldIndex(0);
		setMode("edit-education");
		setError(null);
	};

	const startEditAward = (award: Award) => {
		setForm({
			...emptyForm,
			title: award.title,
			issuer: award.issuer,
			date: award.date,
			description: award.description || "",
		});
		setEditingId(award.id);
		setFormFieldIndex(0);
		setMode("edit-award");
		setError(null);
	};

	const currentFields = mode === "add-education" || mode === "edit-education" ? educationFields : awardFields;

	useKeyboard((key) => {
		// Handle delete confirmation mode
		if (mode === "confirm-delete") {
			if (key.name === "y") {
				if (selectedColumn === "education" && education[selectedIndex]) {
					void handleDeleteEducation(education[selectedIndex].id);
				} else if (selectedColumn === "awards" && awards[selectedIndex]) {
					void handleDeleteAward(awards[selectedIndex].id);
				}
			} else if (key.name === "n" || key.name === "escape") {
				setMode("view");
			}
			return;
		}

		// Handle form mode (add/edit)
		if (mode !== "view") {
			if (key.name === "escape") {
				setForm(emptyForm);
				setEditingId(null);
				setMode("view");
				setError(null);
				return;
			}

			if (key.name === "tab" || key.name === "down") {
				setFormFieldIndex((prev) => (prev + 1) % currentFields.length);
				return;
			}

			if (key.name === "up") {
				setFormFieldIndex((prev) => (prev - 1 + currentFields.length) % currentFields.length);
				return;
			}

			if (key.name === "return") {
				if (mode === "add-education") {
					void handleCreateEducation();
				} else if (mode === "add-award") {
					void handleCreateAward();
				} else if (mode === "edit-education") {
					void handleUpdateEducation();
				} else if (mode === "edit-award") {
					void handleUpdateAward();
				}
				return;
			}

			// Handle text input
			const currentField = currentFields[formFieldIndex];
			if (!currentField) return;
			
			if (key.name === "backspace") {
				setForm((prev) => ({
					...prev,
					[currentField]: prev[currentField].slice(0, -1),
				}));
			} else if (key.sequence && key.sequence.length === 1 && !key.ctrl && !key.meta) {
				setForm((prev) => ({
					...prev,
					[currentField]: prev[currentField] + key.sequence,
				}));
			}
			return;
		}

		// View mode keyboard handling
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

		// 'n' to add new entry
		if (key.name === "n") {
			if (selectedColumn === "education") {
				startAddEducation();
			} else {
				startAddAward();
			}
			return;
		}

		// 'e' to edit selected entry
		if (key.name === "e") {
			if (selectedColumn === "education" && education[selectedIndex]) {
				startEditEducation(education[selectedIndex]);
			} else if (selectedColumn === "awards" && awards[selectedIndex]) {
				startEditAward(awards[selectedIndex]);
			}
			return;
		}

		// Delete with confirmation
		if (key.name === "delete" || (key.name === "d" && key.ctrl)) {
			const hasSelection =
				(selectedColumn === "education" && education[selectedIndex]) ||
				(selectedColumn === "awards" && awards[selectedIndex]);
			if (hasSelection) {
				setMode("confirm-delete");
			}
			return;
		}

		if (key.name === "return") {
			onNext("analysis");
			return;
		}

		if (key.name === "escape") {
			onNext("identity");
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

	// Render form for add/edit modes
	const renderForm = () => {
		const isEducation = mode === "add-education" || mode === "edit-education";
		const fields = isEducation ? educationFields : awardFields;
		const title = mode.startsWith("add") ? `Add ${isEducation ? "Education" : "Award"}` : `Edit ${isEducation ? "Education" : "Award"}`;

		return (
			<box flexDirection="column" padding={2} border borderColor={theme.goldDim} borderStyle="rounded" width={60}>
				<text>
					<span fg={theme.gold}>
						<strong>✎ {title}</strong>
					</span>
				</text>
				<box flexDirection="column" marginTop={1}>
					{fields.map((field, i) => {
						const isActive = formFieldIndex === i;
						const value = form[field];
						const required = isEducation
							? ["institution", "degree", "start_date"].includes(field)
							: ["title", "issuer", "date"].includes(field);
						const label = field.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

						return (
							<box
								key={field}
								flexDirection="row"
								paddingTop={1}
								paddingBottom={1}
								paddingLeft={1}
								paddingRight={1}
								backgroundColor={isActive ? theme.bgMedium : undefined}
							>
								<box width={16}>
									<text>
										<span fg={isActive ? theme.gold : theme.textDim}>
											{label}{required ? <span fg={theme.error}>*</span> : ""}
										</span>
									</text>
								</box>
								<box flexGrow={1}>
									<text>
										<span fg={isActive ? theme.textPrimary : theme.textSecondary}>
											{value || (isActive ? "" : "—")}{isActive && "▌"}
										</span>
									</text>
								</box>
							</box>
						);
					})}
				</box>
				<box marginTop={2} flexDirection="row" justifyContent="space-between">
					<text>
						<span fg={theme.textDim}>
							↑↓ Navigate  •  Enter Save  •  Esc Cancel
						</span>
					</text>
				</box>
				{error && (
					<box marginTop={1}>
						<text>
							<span fg={theme.error}>⚠ {error}</span>
						</text>
					</box>
				)}
			</box>
		);
	};

	// Render delete confirmation
	const renderDeleteConfirmation = () => {
		const item = selectedColumn === "education" ? education[selectedIndex] : awards[selectedIndex];
		const itemName = selectedColumn === "education"
			? `${(item as Education)?.institution} - ${(item as Education)?.degree}`
			: (item as Award)?.title;

		return (
			<box flexDirection="column" padding={2} border borderColor={theme.error} borderStyle="rounded" width={50}>
				<text>
					<span fg={theme.error}>
						<strong>⚠ Confirm Delete</strong>
					</span>
				</text>
				<box marginTop={1}>
					<text>
						<span fg={theme.textPrimary}>
							Are you sure you want to delete:
						</span>
					</text>
				</box>
				<box marginTop={1} paddingLeft={2}>
					<text>
						<span fg={theme.cyan}>
							"{itemName}"
						</span>
					</text>
				</box>
				<box marginTop={2} flexDirection="row" gap={2}>
					<text>
						<span fg={theme.success}>
							<strong>[Y]</strong> Yes, delete
						</span>
					</text>
					<text>
						<span fg={theme.error}>
							<strong>[N]</strong> No, cancel
						</span>
					</text>
				</box>
			</box>
		);
	};

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				title="Education & Awards"
				description="Manage your education and awards"
			/>

			{error && mode === "view" && (
				<box padding={1} backgroundColor={theme.error}>
					<text>
						<span fg={theme.textPrimary}>Error: {error}</span>
					</text>
				</box>
			)}

			{loading ? (
				<box padding={2}>
					<text>
						<span fg={theme.textSecondary}>Loading...</span>
					</text>
				</box>
			) : mode === "confirm-delete" ? (
				<box padding={2}>{renderDeleteConfirmation()}</box>
			) : mode !== "view" ? (
				<box padding={2}>{renderForm()}</box>
			) : (
				<box flexDirection="column" flexGrow={1} padding={2} gap={2}>
					<box flexDirection="row" gap={4} flexGrow={1}>
						{/* Education Column */}
						<box flexDirection="column" flexGrow={1} border borderColor={selectedColumn === "education" ? theme.goldDim : theme.textDim} borderStyle="rounded" padding={1}>
							<box marginBottom={1}>
								<text>
									<span
										fg={
											selectedColumn === "education" ? theme.gold : theme.textDim
										}
									>
										<strong>📚 EDUCATION ({education.length})</strong>
									</span>
								</text>
							</box>
							<box flexDirection="column">
								{educationLines.length > 0 ? (
									educationLines.map((line, i) => (
										<box 
											key={education[i]?.id ?? line}
											paddingLeft={1}
											backgroundColor={selectedColumn === "education" && selectedIndex === i ? theme.bgMedium : undefined}
										>
											<text>
												<span fg={selectedColumn === "education" && selectedIndex === i ? theme.textPrimary : theme.textSecondary}>{line}</span>
											</text>
										</box>
									))
								) : (
									<box paddingLeft={1}>
										<text>
											<span fg={theme.textDim}>No education entries yet</span>
										</text>
									</box>
								)}
							</box>

							{educationDetails && selectedColumn === "education" && (
								<box
									flexDirection="column"
									marginTop={2}
									padding={1}
								>
									<text>
										<span fg={theme.textDim}>────────────────────</span>
									</text>
									<text>
										<span fg={theme.textDim}>Details:</span>
									</text>
									<box paddingLeft={1} marginTop={1}>
										<text>
											<span fg={theme.cyan}>
												Field: {educationDetails.field_of_study || "—"}
											</span>
										</text>
									</box>
									<box paddingLeft={1}>
										<text>
											<span fg={theme.cyan}>
												GPA: {educationDetails.gpa || "—"}
											</span>
										</text>
									</box>
									<box paddingLeft={1}>
										<text>
											<span fg={theme.cyan}>
												Honors: {educationDetails.honors || "—"}
											</span>
										</text>
									</box>
									{educationDetails.end_date && (
										<box paddingLeft={1}>
											<text>
												<span fg={theme.cyan}>
													End: {educationDetails.end_date}
												</span>
											</text>
										</box>
									)}
								</box>
							)}
						</box>

						{/* Awards Column */}
						<box flexDirection="column" flexGrow={1} border borderColor={selectedColumn === "awards" ? theme.goldDim : theme.textDim} borderStyle="rounded" padding={1}>
							<box marginBottom={1}>
								<text>
									<span
										fg={selectedColumn === "awards" ? theme.gold : theme.textDim}
									>
										<strong>🏆 AWARDS ({awards.length})</strong>
									</span>
								</text>
							</box>
							<box flexDirection="column">
								{awardLines.length > 0 ? (
									awardLines.map((line, i) => (
										<box 
											key={awards[i]?.id ?? line}
											paddingLeft={1}
											backgroundColor={selectedColumn === "awards" && selectedIndex === i ? theme.bgMedium : undefined}
										>
											<text>
												<span fg={selectedColumn === "awards" && selectedIndex === i ? theme.textPrimary : theme.textSecondary}>{line}</span>
											</text>
										</box>
									))
								) : (
									<box paddingLeft={1}>
										<text>
											<span fg={theme.textDim}>No awards yet</span>
										</text>
									</box>
								)}
							</box>

							{awardDetails && selectedColumn === "awards" && (
								<box
									flexDirection="column"
									marginTop={2}
									padding={1}
								>
									<text>
										<span fg={theme.textDim}>────────────────────</span>
									</text>
									<text>
										<span fg={theme.textDim}>Description:</span>
									</text>
									<box paddingLeft={1} marginTop={1}>
										<text>
											<span fg={theme.cyan}>
												{awardDetails.description || "—"}
											</span>
										</text>
									</box>
								</box>
							)}
						</box>
					</box>

					<box marginTop={1} paddingTop={1}>
						<text>
							<span fg={theme.textDim}>
								────────────────────────────────────────────────────────────────
							</span>
						</text>
						<text>
							<span fg={theme.textDim}>
								↑↓ Navigate  •  ←→ Switch Column  •  <span fg={theme.gold}>n</span> New  •  <span fg={theme.cyan}>e</span> Edit  •  <span fg={theme.error}>Del</span> Remove  •  Enter Continue  •  Esc Back
							</span>
						</text>
					</box>
				</box>
			)}
		</box>
	);
}
