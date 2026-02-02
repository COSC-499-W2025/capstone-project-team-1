import { useKeyboard } from "@opentui/react";
import { useState } from "react";
import { theme } from "../types";
import { TopBar } from "./TopBar";

interface UserConfigScreenProps {
	onContinue: () => void;
	onBack: () => void;
}

const mockQuestions = [
	{
		id: "email",
		label: "Email address",
		hint: "Used to scope summaries",
		placeholder: "you@example.com",
		value: "ahmad@example.com",
	},
	{
		id: "role",
		label: "Target role",
		hint: "Tailor the resume tone",
		placeholder: "Frontend Engineer",
		value: "Product Engineer",
	},
	{
		id: "focus",
		label: "Focus areas",
		hint: "Comma-separated",
		placeholder: "React, UI systems, DX",
		value: "TypeScript, design systems",
	},
	{
		id: "style",
		label: "Writing style",
		hint: "Concise or detailed",
		placeholder: "Concise",
		value: "Concise",
	},
];

export function UserConfigScreen({ onContinue, onBack }: UserConfigScreenProps) {
	const [focusIndex, setFocusIndex] = useState(0);
	const totalFocusable = mockQuestions.length + 1;

	useKeyboard((key) => {
		if (key.name === "tab") {
			setFocusIndex((prev) => (prev + 1) % totalFocusable);
		}
		if (key.name === "return") {
			if (focusIndex === mockQuestions.length) {
				onContinue();
			} else {
				setFocusIndex((prev) => (prev + 1) % totalFocusable);
			}
		}
		if (key.name === "escape") {
			onBack();
		}
	});

	const focusedQuestion = mockQuestions[Math.min(focusIndex, mockQuestions.length - 1)];

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Setup"
				title="User Configuration"
				description="Answer a few questions to personalize your resume."
			/>

			<box flexGrow={1} flexDirection="row" padding={2} gap={2}>
				<box
					width="55%"
					border
					borderStyle="rounded"
					borderColor={theme.gold}
					flexDirection="column"
					padding={2}
					gap={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>Questions</strong>
						</span>
					</text>
					{mockQuestions.map((question, index) => {
						const isFocused = focusIndex === index;
						return (
							<box
								key={question.id}
								backgroundColor={isFocused ? theme.bgLight : undefined}
								paddingLeft={1}
								paddingRight={1}
								paddingTop={1}
								paddingBottom={1}
							>
								<text>
									<span fg={isFocused ? theme.cyan : theme.textSecondary}>
										{index + 1}. {question.label}
									</span>
								</text>
								<text>
									<span fg={theme.textDim}>{question.placeholder}</span>
								</text>
							</box>
						);
					})}

					<box
						marginTop={1}
						border
						borderStyle="single"
						borderColor={
							focusIndex === mockQuestions.length ? theme.cyan : theme.textDim
						}
						padding={1}
					>
						<text>
							<span fg={theme.textPrimary}>Continue</span>
							<span fg={theme.textDim}> (Enter)</span>
						</text>
					</box>
				</box>

				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={theme.textDim}
					flexDirection="column"
					padding={2}
					gap={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>Answer Preview</strong>
						</span>
					</text>
					<text>
						<span fg={theme.textDim}>Field:</span>
						<span fg={theme.textPrimary}> {focusedQuestion?.label}</span>
					</text>
					<text>
						<span fg={theme.textDim}>Hint:</span>
						<span fg={theme.textSecondary}> {focusedQuestion?.hint}</span>
					</text>
					<box
						marginTop={1}
						border
						borderStyle="single"
						borderColor={theme.cyanDim}
						padding={1}
					>
						<text>
							<span fg={theme.textDim}>Current value</span>
						</text>
						<text>
							<span fg={theme.textPrimary}>
								{focusedQuestion?.value}
							</span>
						</text>
					</box>

					<box marginTop={1} flexDirection="column" gap={1}>
						<text>
							<span fg={theme.textDim}>Navigation</span>
						</text>
						<text>
							<span fg={theme.textDim}>Tab:</span>
							<span fg={theme.textSecondary}> next field</span>
						</text>
						<text>
							<span fg={theme.textDim}>Esc:</span>
							<span fg={theme.textSecondary}> back</span>
						</text>
					</box>
				</box>
			</box>

			<box
				height={3}
				border
				borderStyle="single"
				borderColor={theme.error}
				paddingLeft={2}
				paddingRight={2}
				paddingTop={1}
				paddingBottom={1}
			>
				<text>
					<span fg={theme.goldDark}>Demo Mode:</span>
					<span fg={theme.textDim}> Press </span>
					<span fg={theme.cyan}>Tab</span>
					<span fg={theme.textDim}> to move, </span>
					<span fg={theme.cyan}>Enter</span>
					<span fg={theme.textDim}> to continue</span>
				</text>
			</box>
		</box>
	);
}
