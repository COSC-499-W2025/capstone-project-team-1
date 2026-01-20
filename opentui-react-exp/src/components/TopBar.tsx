import { theme } from "../types";

interface TopBarProps {
  title: string;
  subTitle?: string;
}

export function TopBar({ title, subTitle }: TopBarProps) {
  return (
    <box
      width="100%"
      flexDirection="row"
      justifyContent="center"
      alignItems="center"
      gap={1}
      padding={1}
      backgroundColor={theme.bgDark}
    >
      <text>
        <span fg={theme.gold}>{title}</span>
      </text>
      {subTitle && (
        <text>
          <span fg={theme.textDim}> | </span>
          <span fg={theme.cyan}>{subTitle}</span>
        </text>
      )}
    </box>
  );
}
