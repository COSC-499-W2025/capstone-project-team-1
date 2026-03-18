import type { KeyAction } from "../types";
import { theme } from "../types";

interface BottomBarProps {
	actions: KeyAction[];
	onBack?: () => void;
	onForward?: () => void;
	forwardLabel?: string;
}

export function BottomBar({ actions, onBack, onForward, forwardLabel = "Continue" }: BottomBarProps) {
	return (
		<box
			width="100%"
			flexDirection="row"
			alignItems="center"
			paddingLeft={2}
			paddingRight={2}
			height={1}
			backgroundColor={theme.bgDark}
		>
			{/* Left: back button */}
			<box width={10}>
				{onBack ? (
					<box onMouseDown={onBack}>
						<text>
							<span fg={theme.textDim}>{"‹ back"}</span>
						</text>
					</box>
				) : null}
			</box>

			{/* Center: keyboard shortcuts */}
			<box flexGrow={1} flexDirection="row" justifyContent="center" gap={3}>
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

			{/* Right: forward button */}
			<box width={14}>
				{onForward ? (
					<box onMouseDown={onForward}>
						<text>
							<span fg={theme.gold}>{forwardLabel}{" ›"}</span>
						</text>
					</box>
				) : null}
			</box>
		</box>
	);
}
