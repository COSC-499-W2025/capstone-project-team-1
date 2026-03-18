import type { ReactNode } from "react";

interface ClickableBoxProps {
	onClick: () => void;
	children: ReactNode;
	/** Whether this item is currently selected/active */
	selected?: boolean;
	/** Border color when not selected */
	borderColor?: string;
	/** Border color when selected */
	selectedBorderColor?: string;
	/** Background when not selected */
	backgroundColor?: string;
	/** Background when selected */
	selectedBackgroundColor?: string;
	/** Show a border (defaults to true) */
	border?: boolean;
	/** Border style */
	borderStyle?: "single" | "double" | "rounded" | "bold";
	/** Additional box layout props */
	flexGrow?: number;
	flexDirection?: "row" | "column";
	padding?: number;
	paddingLeft?: number;
	paddingRight?: number;
	paddingTop?: number;
	paddingBottom?: number;
	gap?: number;
	width?: number | string;
	height?: number | string;
	justifyContent?: string;
	alignItems?: string;
}

/**
 * A <box> wrapper that responds to mouse clicks.
 * Visually distinguishes selected vs unselected state via border and background colors.
 */
export function ClickableBox({
	onClick,
	children,
	selected = false,
	borderColor = "#888888",
	selectedBorderColor = "#FFD700",
	backgroundColor = "#000000",
	selectedBackgroundColor = "#1a1a00",
	border = true,
	borderStyle = "rounded",
	...layoutProps
}: ClickableBoxProps) {
	return (
		<box
			border={border}
			borderStyle={borderStyle}
			borderColor={selected ? selectedBorderColor : borderColor}
			backgroundColor={selected ? selectedBackgroundColor : backgroundColor}
			onMouseDown={onClick}
			{...layoutProps}
		>
			{children}
		</box>
	);
}

interface ClickableListItem {
	id: string;
	label: string;
	description?: string;
}

interface ClickableListProps {
	items: ClickableListItem[];
	selectedId: string | null;
	onSelect: (id: string, index: number) => void;
	/** Text color for unselected items */
	textColor?: string;
	/** Text color for selected item */
	selectedTextColor?: string;
	/** Background for even rows */
	evenRowBg?: string;
	/** Background for odd rows */
	oddRowBg?: string;
	/** Background for selected row */
	selectedRowBg?: string;
	/** Height of the scrollable area */
	height?: number;
	/** Whether the scrollbox has keyboard focus */
	focused?: boolean;
}

/**
 * A scrollable, clickable list that replaces <select> with mouse support.
 * Each item is a <box> with onMouseDown for click-to-select.
 */
export function ClickableList({
	items,
	selectedId,
	onSelect,
	textColor = "#CCCCCC",
	selectedTextColor = "#00FF00",
	evenRowBg = "#1a1a1a",
	oddRowBg = "#222222",
	selectedRowBg = "#004444",
	height = 16,
	focused = true,
}: ClickableListProps) {
	return (
		<scrollbox height={height} focused={focused}>
			{items.map((item, i) => {
				const isSelected = item.id === selectedId;
				const bg = isSelected
					? selectedRowBg
					: i % 2 === 0
						? evenRowBg
						: oddRowBg;
				return (
					<box
						key={item.id}
						backgroundColor={bg}
						paddingLeft={1}
						paddingRight={1}
						onMouseDown={() => onSelect(item.id, i)}
					>
						<text fg={isSelected ? selectedTextColor : textColor}>
							{isSelected ? "> " : "  "}
							<strong>{item.label}</strong>
							{item.description ? (
								<span fg={isSelected ? "#88DDDD" : "#888888"}>
									{" "}
									{item.description}
								</span>
							) : null}
						</text>
					</box>
				);
			})}
		</scrollbox>
	);
}
