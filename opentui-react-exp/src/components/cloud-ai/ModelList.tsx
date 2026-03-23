/**
 * Centered card with a success banner and vertical model radio list.
 *
 * Shared between CopilotLogin (post-auth) and CloudAuth (already-authed).
 */
import { useState } from "react";
import { useKeyboard } from "@opentui/react";
import { theme } from "../../types";
import { CLOUD_MODELS, DEFAULT_MODEL_ID } from "./ModelPicker";

interface ModelListProps {
	successMessage: string;
	onSelect: (modelId: string) => void;
	onBack: () => void;
}

export function ModelList({ successMessage, onSelect, onBack }: ModelListProps) {
	const [selected, setSelected] = useState(
		Math.max(0, CLOUD_MODELS.findIndex((m) => m.id === DEFAULT_MODEL_ID)),
	);

	useKeyboard((key) => {
		if (key.name === "up") {
			setSelected((i) => Math.max(0, i - 1));
		} else if (key.name === "down") {
			setSelected((i) => Math.min(CLOUD_MODELS.length - 1, i + 1));
		} else if (key.name === "return") {
			onSelect(CLOUD_MODELS[selected]!.id);
		} else if (key.name === "escape") {
			onBack();
		}
	});

	return (
		<box
			flexGrow={1}
			flexDirection="column"
			alignItems="center"
			justifyContent="center"
		>
			<box
				flexDirection="column"
				border
				borderStyle="rounded"
				borderColor={theme.textDim}
				padding={2}
				gap={1}
				width={55}
			>
				{/* Success banner */}
				<text>
					<span fg={theme.success}>
						<strong>{successMessage}</strong>
					</span>
				</text>

				{/* Heading */}
				<box paddingTop={1}>
					<text>
						<span fg={theme.textSecondary}>
							Choose a model for resume generation:
						</span>
					</text>
				</box>

				{/* Model list */}
				<box flexDirection="column" paddingTop={1} gap={1}>
					{CLOUD_MODELS.map((model, i) => {
						const isSelected = i === selected;
						const bullet = isSelected ? "●" : "○";
						const bulletColor = isSelected ? theme.gold : theme.textDim;
						const nameColor = isSelected ? theme.gold : theme.textSecondary;
						const descColor = isSelected ? theme.textSecondary : theme.textDim;

						return (
							<box
								key={model.id}
								flexDirection="column"
								paddingLeft={1}
								paddingRight={1}
								onMouseDown={() => setSelected(i)}
								onMouseUp={() => onSelect(CLOUD_MODELS[i]!.id)}
							>
								<text>
									<span fg={bulletColor}>{bullet} </span>
									<span fg={nameColor}>
										<strong>{model.name}</strong>
									</span>
									<span fg={theme.textDim}> · {model.provider}</span>
								</text>
								<text>
									<span fg={descColor}>{"   "}{model.description}</span>
								</text>
							</box>
						);
					})}
				</box>

				{/* Confirm button */}
				<box flexDirection="row" justifyContent="center" paddingTop={1}>
					<box
						border
						borderStyle="rounded"
						borderColor={theme.gold}
						backgroundColor="#1a1a00"
						paddingLeft={2}
						paddingRight={2}
						onMouseDown={() => onSelect(CLOUD_MODELS[selected]!.id)}
					>
						<text>
							<span fg={theme.gold}>
								<strong>Confirm</strong>
							</span>
						</text>
					</box>
				</box>
			</box>
		</box>
	);
}
