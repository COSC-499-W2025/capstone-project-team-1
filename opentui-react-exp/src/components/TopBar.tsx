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
			gap={0}
			padding={1}
			backgroundColor={theme.bgDark}
		>
			<box width="100%" flexDirection="row" alignItems="center">
				{/* Left side: Step (aligned right) */}
				<box
					flexGrow={1}
					width={0}
					flexDirection="row"
					justifyContent="flex-end"
					paddingRight={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>{step}</strong>
						</span>
					</text>
				</box>

				{/* Center: Separator */}
				<text>
					<span fg={theme.textDim}>|</span>
				</text>

				{/* Right side: Title (aligned left) */}
				<box
					flexGrow={1}
					width={0}
					flexDirection="row"
					justifyContent="flex-start"
					paddingLeft={0.5}
				>
					<text>
						<span fg={theme.textPrimary}>
							<strong>{title}</strong>
						</span>
					</text>
				</box>
			</box>

			{description && (
				<text>
					<span fg={theme.textDim}>{description}</span>
				</text>
			)}
		</box>
	);
}
