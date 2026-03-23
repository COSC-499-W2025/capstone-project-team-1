/**
 * Centered card with a success banner, user identity, and vertical model radio list.
 *
 * Shared between CopilotLogin (post-auth) and CloudAuth (already-authed).
 */
import { useState } from "react";
import { useKeyboard } from "@opentui/react";
import type { GitHubUser } from "../../agent";
import { theme } from "../../types";
import { useToast } from "../Toast";
import { CLOUD_MODELS, DEFAULT_MODEL_ID } from "./ModelPicker";

export interface ModelListResult {
	modelId: string;
	gitIdentity: { login: string; name: string | null; email: string };
}

interface ModelListProps {
	successMessage: string;
	user: GitHubUser | null;
	onSelect: (result: ModelListResult) => void;
	onBack: () => void;
}

export function ModelList({ successMessage, user, onSelect, onBack }: ModelListProps) {
	const toast = useToast();
	const hasAutoEmail = Boolean(user?.email);
	const [selected, setSelected] = useState(
		Math.max(0, CLOUD_MODELS.findIndex((m) => m.id === DEFAULT_MODEL_ID)),
	);
	const [emailInput, setEmailInput] = useState(user?.email ?? "");
	const [editingEmail, setEditingEmail] = useState(!hasAutoEmail);

	const handleConfirm = () => {
		if (editingEmail && !hasAutoEmail) {
			// They're still in the input but we allow confirm if they typed something
			if (!emailInput.trim()) {
				toast.show({ variant: "error", message: "Please enter your GitHub email to continue" });
				return;
			}
			setEditingEmail(false);
		}
		if (!emailInput.trim()) {
			toast.show({ variant: "error", message: "Please enter your GitHub email to continue" });
			setEditingEmail(true);
			return;
		}
		onSelect({
			modelId: CLOUD_MODELS[selected]!.id,
			gitIdentity: {
				login: user?.login ?? "",
				name: user?.name ?? null,
				email: emailInput.trim(),
			},
		});
	};

	useKeyboard((key) => {
		if (editingEmail) {
			if (key.name === "escape") {
				if (hasAutoEmail) {
					// Revert to auto-detected email and exit editing
					setEmailInput(user?.email ?? "");
					setEditingEmail(false);
				} else {
					// No auto email — Esc goes back
					onBack();
				}
			} else if (key.name === "return") {
				if (!emailInput.trim() && !hasAutoEmail) {
					toast.show({ variant: "error", message: "Please enter your GitHub email to continue" });
					return;
				}
				setEditingEmail(false);
			} else if (key.name === "backspace") {
				setEmailInput((v) => v.slice(0, -1));
			} else if (key.sequence && key.sequence.length === 1 && !key.ctrl && !key.meta) {
				setEmailInput((v) => v + key.sequence);
			}
			return;
		}

		if (key.name === "up") {
			setSelected((i) => Math.max(0, i - 1));
		} else if (key.name === "down") {
			setSelected((i) => Math.min(CLOUD_MODELS.length - 1, i + 1));
		} else if (key.name === "e") {
			setEditingEmail(true);
		} else if (key.name === "return") {
			handleConfirm();
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
				width={58}
			>
				{/* Success banner */}
				<text>
					<span fg={theme.success}>
						<strong>{successMessage}</strong>
					</span>
				</text>

				{/* User identity */}
				{user && (
					<box flexDirection="column" paddingTop={0}>
						<text>
							<span fg={theme.textSecondary}>
								{"  "}Signed in as{" "}
							</span>
							<span fg={theme.gold}>
								<strong>{user.login}</strong>
							</span>
							{user.name && (
								<span fg={theme.textDim}> ({user.name})</span>
							)}
						</text>
					</box>
				)}

				{/* Email section */}
				<box flexDirection="column" paddingLeft={2} gap={0}>
					{editingEmail ? (
						<>
							<text>
								<span fg={theme.textSecondary}>
									{hasAutoEmail ? "Email:" : "Enter your GitHub email:"}
								</span>
							</text>
							<box
								border
								borderStyle="single"
								borderColor={theme.cyan}
								paddingLeft={1}
								paddingRight={1}
								width={40}
							>
								<text>
									<span fg={theme.textPrimary}>
										{emailInput || " "}
									</span>
									<span fg={theme.cyan}>_</span>
								</text>
							</box>
						</>
					) : (
						<>
							<text>
								<span fg={theme.textDim}>{emailInput}</span>
							</text>
							<text>
								<span fg={theme.textDim}>
									Press{" "}
								</span>
								<span fg={theme.cyan}>e</span>
								<span fg={theme.textDim}>
									{" "}to change email
								</span>
							</text>
						</>
					)}
				</box>

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
								onMouseUp={handleConfirm}
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
						onMouseDown={handleConfirm}
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
