import { theme } from "../types";

interface TopBarProps {
	step: string;
	title: string;
	description?: string;
}

export function TopBar({ step, title, description }: TopBarProps) {
	return (
		<box
			width="100%"
			flexDirection="column"
			justifyContent="center"
			alignItems="center"
			paddingTop={1}
			paddingBottom={1}
			backgroundColor={theme.bgDark}
		>
			<text>
				<span fg={theme.gold}>
					<strong>{step}</strong>
				</span>
				<span fg={theme.textDim}>{" | "}</span>
				<span fg={theme.textPrimary}>
					<strong>{title}</strong>
				</span>
			</text>
			{description && (
				<text>
					<span fg={theme.textDim}>{description}</span>
				</text>
			)}
		</box>
	);
}
