import type { KeyAction } from "../types";
import { theme } from "../types";

interface BottomBarProps {
	hint?: string;
	actions: KeyAction[];
}

export function BottomBar({ hint, actions }: BottomBarProps) {
	return (
		<box
			width="100%"
			flexDirection="row"
			justifyContent="space-between"
			paddingLeft={2}
			paddingRight={2}
			paddingTop={1}
			paddingBottom={1}
			backgroundColor={theme.bgDark}
		>
			<text>
				<span fg={theme.textDim}>{hint ?? ""}</span>
			</text>

			<box flexDirection="row" gap={4}>
				{actions.map((action) => (
					<box key={`${action.key}-${action.label}`} flexDirection="row" gap={1}>
						<text>
							<span fg={theme.goldDark}>{action.key}</span>
						</text>
						<text>
							<span fg={theme.textDim}>{action.label}</span>
						</text>
					</box>
				))}
			</box>
		</box>
	);
}
