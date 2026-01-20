import { useState, useEffect } from "react";
import { theme } from "../types";

interface LandingProps {
  onGetStarted: () => void;
}

const TITLE = "ARTIFACT MINER";

// Gold color cycle for pulsing border glow
const glowColors = [
  "#FFD700", // gold
  "#FFDF33", // lighter gold
  "#FFC700", // amber gold
  "#FFB700", // darker gold
  "#FFC700",
  "#FFDF33",
];

export function Landing({ onGetStarted }: LandingProps) {
  // Typewriter reveal state
  const [revealedChars, setRevealedChars] = useState(0);
  const [showCursor, setShowCursor] = useState(true);

  // Pulsing border glow state
  const [glowIndex, setGlowIndex] = useState(0);

  // Typewriter effect: reveal title letter by letter
  useEffect(() => {
    if (revealedChars < TITLE.length) {
      const timer = setTimeout(() => {
        setRevealedChars((c) => c + 1);
      }, 80); // 80ms per character
      return () => clearTimeout(timer);
    }
  }, [revealedChars]);

  // Blinking cursor effect
  useEffect(() => {
    const cursorInterval = setInterval(() => {
      setShowCursor((c) => !c);
    }, 500);
    return () => clearInterval(cursorInterval);
  }, []);

  // Pulsing glow effect on button border
  useEffect(() => {
    const glowInterval = setInterval(() => {
      setGlowIndex((i) => (i + 1) % glowColors.length);
    }, 400);
    return () => clearInterval(glowInterval);
  }, []);

  const revealedText = TITLE.slice(0, revealedChars);
  const cursor = showCursor && revealedChars < TITLE.length ? "▌" : "";

  return (
    <box
      flexGrow={1}
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      backgroundColor="#000000"
      gap={10}
    >
      {/* Title Section with typewriter effect */}
      <box flexDirection="column" alignItems="center" gap={1}>
        <ascii-font font="block" text={revealedText + cursor} color={theme.gold} />
        <text>
          <span fg={theme.goldDark}>
            Transform your code into a professional resume
          </span>
        </text>
      </box>

      {/* Get Started Button with pulsing glow */}
      <box
        border
        borderStyle="rounded"
        borderColor={glowColors[glowIndex]}
        backgroundColor="#1a1a00"
        paddingLeft={4}
        paddingRight={4}
        paddingTop={1}
        paddingBottom={1}
        onMouseDown={onGetStarted}
      >
        <text>
          <span fg={theme.gold}>
            <strong>Get Started</strong>
          </span>
        </text>
      </box>

      {/* Feature highlights */}
      {/* <box flexDirection="column" alignItems="center" gap={0} marginTop={2}>
        <text>
          <span fg={theme.cyan}>Upload</span>
          <span fg={theme.textDim}> your projects </span>
          <span fg={theme.cyan}>→</span>
          <span fg={theme.textDim}> Analyze code </span>
          <span fg={theme.cyan}>→</span>
          <span fg={theme.textDim}> Generate resume</span>
        </text>
      </box> */}
    </box>
  );
}
