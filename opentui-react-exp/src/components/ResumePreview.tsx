import { theme, type ResumeData } from "../types";

interface ResumePreviewProps {
  data: ResumeData;
  onBack: () => void;
  onRestart: () => void;
}

export function ResumePreview({ data, onBack, onRestart }: ResumePreviewProps) {
  const expertSkills = data.skills.filter((s) => s.level === "expert");
  const advancedSkills = data.skills.filter((s) => s.level === "advanced");
  const intermediateSkills = data.skills.filter((s) => s.level === "intermediate");

  return (
    <box
      flexGrow={1}
      flexDirection="column"
      backgroundColor={theme.bgDark}
    >
      {/* Header */}
      <box
        paddingLeft={2}
        paddingTop={1}
        paddingBottom={1}
        backgroundColor={theme.bgMedium}
        flexDirection="row"
        justifyContent="space-between"
        paddingRight={2}
      >
        <text>
          <span fg={theme.gold}>
            <strong>Resume Generated!</strong>
          </span>
        </text>
        <text>
          <span fg={theme.success}>✓ Analysis complete</span>
        </text>
      </box>

      {/* Resume content */}
      <scrollbox
        focused
        style={{
          rootOptions: { backgroundColor: theme.bgDark },
          wrapperOptions: { flexGrow: 1 },
          viewportOptions: { padding: 2 },
        }}
      >
        <box flexDirection="column" gap={2}>
          {/* Summary section */}
          <box
            flexDirection="column"
            border
            borderStyle="rounded"
            borderColor={theme.gold}
            padding={2}
          >
            <text>
              <span fg={theme.gold}>
                <strong>Professional Summary</strong>
              </span>
            </text>
            <text>
              <span fg={theme.textSecondary}>{data.summary}</span>
            </text>
          </box>

          {/* Skills section */}
          <box flexDirection="column" gap={1}>
            <text>
              <span fg={theme.cyan}>
                <strong>Technical Skills</strong>
              </span>
            </text>
            
            {expertSkills.length > 0 && (
              <box flexDirection="row" gap={1}>
                <text>
                  <span fg={theme.textDim}>Expert:</span>
                </text>
                <box flexDirection="row" gap={1} flexWrap="wrap">
                  {expertSkills.map((skill, i) => (
                    <box key={i} backgroundColor={theme.goldDim} paddingLeft={1} paddingRight={1}>
                      <text>
                        <span fg={theme.textPrimary}>{skill.name}</span>
                      </text>
                    </box>
                  ))}
                </box>
              </box>
            )}
            
            {advancedSkills.length > 0 && (
              <box flexDirection="row" gap={1}>
                <text>
                  <span fg={theme.textDim}>Advanced:</span>
                </text>
                <box flexDirection="row" gap={1} flexWrap="wrap">
                  {advancedSkills.map((skill, i) => (
                    <box key={i} backgroundColor={theme.cyanDim} paddingLeft={1} paddingRight={1}>
                      <text>
                        <span fg={theme.textPrimary}>{skill.name}</span>
                      </text>
                    </box>
                  ))}
                </box>
              </box>
            )}
            
            {intermediateSkills.length > 0 && (
              <box flexDirection="row" gap={1}>
                <text>
                  <span fg={theme.textDim}>Intermediate:</span>
                </text>
                <box flexDirection="row" gap={1} flexWrap="wrap">
                  {intermediateSkills.map((skill, i) => (
                    <box key={i} backgroundColor={theme.bgLight} paddingLeft={1} paddingRight={1}>
                      <text>
                        <span fg={theme.textPrimary}>{skill.name}</span>
                      </text>
                    </box>
                  ))}
                </box>
              </box>
            )}
          </box>

          {/* Projects section */}
          <box flexDirection="column" gap={1}>
            <text>
              <span fg={theme.cyan}>
                <strong>Notable Projects</strong>
              </span>
            </text>
            
            {data.projects.slice(0, 5).map((project) => (
              <box
                key={project.id}
                flexDirection="column"
                border
                borderStyle="single"
                borderColor={theme.textDim}
                padding={1}
                marginBottom={1}
              >
                <box flexDirection="row" justifyContent="space-between">
                  <text>
                    <span fg={theme.gold}>
                      <strong>{project.name}</strong>
                    </span>
                  </text>
                  <text>
                    <span fg={theme.cyan}>{project.language}</span>
                  </text>
                </box>
                <text>
                  <span fg={theme.textSecondary}>{project.description}</span>
                </text>
                <box flexDirection="row" gap={1} marginTop={1}>
                  {project.technologies.slice(0, 5).map((tech, i) => (
                    <text key={i}>
                      <span fg={theme.textDim}>• {tech}</span>
                    </text>
                  ))}
                </box>
              </box>
            ))}
          </box>

          {/* Stats */}
          <box
            flexDirection="row"
            gap={4}
            border
            borderStyle="rounded"
            borderColor={theme.cyanDim}
            padding={2}
            justifyContent="center"
          >
            <box flexDirection="column" alignItems="center">
              <text>
                <span fg={theme.gold}>
                  <strong>{data.projects.length}</strong>
                </span>
              </text>
              <text>
                <span fg={theme.textDim}>Projects</span>
              </text>
            </box>
            <box flexDirection="column" alignItems="center">
              <text>
                <span fg={theme.gold}>
                  <strong>{data.skills.length}</strong>
                </span>
              </text>
              <text>
                <span fg={theme.textDim}>Skills</span>
              </text>
            </box>
            <box flexDirection="column" alignItems="center">
              <text>
                <span fg={theme.gold}>
                  <strong>{data.projects.reduce((sum, p) => sum + p.commits, 0)}</strong>
                </span>
              </text>
              <text>
                <span fg={theme.textDim}>Total Commits</span>
              </text>
            </box>
            <box flexDirection="column" alignItems="center">
              <text>
                <span fg={theme.gold}>
                  <strong>{new Set(data.projects.map((p) => p.language)).size}</strong>
                </span>
              </text>
              <text>
                <span fg={theme.textDim}>Languages</span>
              </text>
            </box>
          </box>
        </box>
      </scrollbox>
    </box>
  );
}
