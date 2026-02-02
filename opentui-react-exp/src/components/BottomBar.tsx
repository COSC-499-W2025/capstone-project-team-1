import type { KeyAction } from "../types";
import { theme } from "../types";

interface BottomBarProps {
	actions: KeyAction[];
}

export function BottomBar({ actions }: BottomBarProps) {
	return (
		<box
			width="100%"
			flexDirection="row"
			justifyContent="center"
			gap={4}
			padding={1}
			backgroundColor={theme.bgDark}
		>
			{actions.map((action, index) => (
				<box key={index} flexDirection="row" gap={1}>
					<text>
						<span fg={theme.goldDark}>{action.key}</span>
					</text>
					<text>
						<span fg={theme.textDim}>{action.label}</span>
					</text>
				</box>
			))}
		</box>
	);
}
