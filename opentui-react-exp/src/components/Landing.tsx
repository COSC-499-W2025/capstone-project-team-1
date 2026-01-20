import { useState, useEffect } from "react";
// import { TopBar } from "./TopBar";
import { theme } from "../types";

interface LandingProps {
  onGetStarted: () => void;
}

const TITLE = "ARTIFACT MINER";
const SUBTITLE = "Transform your code into a professional resume";
const CTA_TEXT = "Get Started";

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

  // CTA ripple state: which character index is currently "highlighted"
  const [rippleIndex, setRippleIndex] = useState(-1);
  const [showSubtitle, setShowSubtitle] = useState(false);

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

  // Show subtitle after title typewriter completes
  useEffect(() => {
    if (revealedChars >= TITLE.length && !showSubtitle) {
      // Small delay before showing subtitle
      const timer = setTimeout(() => {
        setShowSubtitle(true);
        setRippleIndex(0);
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [revealedChars, showSubtitle]);

  // Ripple effect: cycle through CTA characters
  useEffect(() => {
    if (!showSubtitle) {
      return;
    }

    const rippleInterval = setInterval(() => {
      setRippleIndex((i) => (i + 1) % (CTA_TEXT.length + 6)); // +6 for pause at end
    }, 60);

    return () => clearInterval(rippleInterval);
  }, [showSubtitle]);

  const revealedText = TITLE.slice(0, revealedChars);
  const cursor = showCursor ? "|" : " ";

  // Render subtitle without ripple effect
  const renderSubtitle = () => {
    if (!showSubtitle) {
      return null;
    }

    return (
      <text>
        <span fg={theme.goldDark}>{SUBTITLE}</span>
      </text>
    );
  };

  const renderCtaText = () =>
    CTA_TEXT.split("").map((char, i) => {
      const distance = Math.abs(i - rippleIndex);

      let color: string;
      if (distance === 0) {
        color = theme.gold;
      } else if (distance === 1) {
        color = "#E6C200";
      } else if (distance === 2) {
        color = "#CCAA00";
      } else {
        color = theme.goldDark;
      }

      return (
        <span key={i} fg={color}>
          {char}
        </span>
      );
    });

  return (
    <box
      flexGrow={1}
      flexDirection="column"
      backgroundColor="#000000"
    >
      {/* <TopBar 
        step="ARTIFACT MINER" 
        title="Welcome" 
        description="Transform your code into a professional resume"
      /> */}
      <box
        flexGrow={1}
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        gap={10}
      >
        {/* Title Section with typewriter effect */}
      <box flexDirection="column" alignItems="center" gap={1}>
        <ascii-font font="block" text={revealedText + cursor} color={theme.gold} />
        {renderSubtitle()}
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
          <strong>{renderCtaText()}</strong>
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
    </box>
  );
}
