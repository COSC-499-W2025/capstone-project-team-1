import { useEffect, useState } from "react";
// import { TopBar } from "./TopBar";
import { theme } from "../types";

interface LandingProps {
    onGetStarted: () => void;
}

const SUBTITLE_OPTIONS = [
    // "Projects become portfolio",
    "We build your narrative",
    "Your repos, rewritten by us",
    // "From terminal to timeline",
    "Proof of work, now polished by us",
    "Turning your TODOs to ta-das",
];

const getRandomSubtitle = () => {
    const randomIndex = Math.floor(Math.random() * SUBTITLE_OPTIONS.length);
    return SUBTITLE_OPTIONS[randomIndex];
};

const TITLE_SEQUENCE = [getRandomSubtitle(), "ARTIFACT MINER"];
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
    // Typewriter title state
    const [titleText, setTitleText] = useState("");
    const [titlePhase, setTitlePhase] = useState<
        "typing" | "pause" | "deleting"
    >("typing");
    const [titleIndex, setTitleIndex] = useState(0);

    const [rippleIndex, setRippleIndex] = useState(-1);
    const [glowIndex, setGlowIndex] = useState(0);
    const [enableCtaRipple, setEnableCtaRipple] = useState(false);
    const [ctaOpacity, setCtaOpacity] = useState(0);

    // Typewriter effect for the title sequence
    useEffect(() => {
        const targetText = TITLE_SEQUENCE[titleIndex] ?? "";
        let timer: ReturnType<typeof setTimeout> | undefined;

        if (titlePhase === "typing") {
            if (titleText.length < targetText.length) {
                timer = setTimeout(() => {
                    setTitleText(targetText.slice(0, titleText.length + 1));
                }, 80);
            } else {
                timer = setTimeout(() => {
                    setTitlePhase("pause");
                }, 700);
            }
        } else if (titlePhase === "deleting") {
            if (titleText.length > 0) {
                timer = setTimeout(() => {
                    setTitleText(titleText.slice(0, -1));
                }, 45);
            } else {
                setTitlePhase("typing");
                setTitleIndex((index) => index + 1);
            }
        } else if (titlePhase === "pause") {
            if (titleIndex >= TITLE_SEQUENCE.length - 1) {
                setEnableCtaRipple(true);
                return undefined;
            }

            timer = setTimeout(() => {
                setTitlePhase("deleting");
            }, 700);
        }

        return () => {
            if (timer) {
                clearTimeout(timer);
            }
        };
    }, [titleIndex, titlePhase, titleText]);

    // Pulsing glow effect on button border
    useEffect(() => {
        const glowInterval = setInterval(() => {
            setGlowIndex((i) => (i + 1) % glowColors.length);
        }, 400);
        return () => clearInterval(glowInterval);
    }, []);

    // Ripple effect: cycle through CTA characters
    useEffect(() => {
        if (!enableCtaRipple) {
            return;
        }

        setCtaOpacity(0);
        const fadeStep = 1 / 12;
        const fadeInterval = setInterval(() => {
            setCtaOpacity((value) => Math.min(1, value + fadeStep));
        }, 50);

        const rippleInterval = setInterval(() => {
            setRippleIndex((i) => (i + 1) % (CTA_TEXT.length + 6)); // +6 for pause at end
        }, 60);

        return () => {
            clearInterval(rippleInterval);
            clearInterval(fadeInterval);
        };
    }, [enableCtaRipple]);

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

    const renderTitle = () => {
        if (titleIndex === 0) {
            return (
                <text>
                    <span fg={theme.gold}>{titleText}</span>
                </text>
            );
        }

        return <ascii-font font="block" text={titleText} color={theme.gold} />;
    };

    return (
        <box flexGrow={1} flexDirection="column" backgroundColor="#000000">
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
                gap={3}
            >
                {/* Title Section with typewriter effect */}
                <box
                    flexDirection="column"
                    alignItems="center"
                    justifyContent="center"
                    gap={1}
                    height={8}
                >
                    <box flexDirection="row" alignItems="flex-end" gap={1}>
                        {renderTitle()}
                    </box>
                </box>

                {/* Get Started Button with pulsing glow */}
                {enableCtaRipple ? (
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
                        style={{ opacity: ctaOpacity }}
                    >
                        <text>
                            <strong>{renderCtaText()}</strong>
                        </text>
                    </box>
                ) : null}

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
