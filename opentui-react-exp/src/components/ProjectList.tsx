import { useState } from "react";
import { TopBar } from "./TopBar";
import { theme, type Project } from "../types";
import { mockProjects } from "../data/mockProjects";

interface ProjectListProps {
  projects: Project[];
  onContinue: () => void;
  onBack: () => void;
}

export function ProjectList({ projects, onContinue, onBack }: ProjectListProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const selectedProject = projects[selectedIndex];

  return (
    <box
      flexGrow={1}
      flexDirection="column"
      backgroundColor={theme.bgDark}
    >
      <TopBar 
        step="Step 2" 
        title="Review Detected Projects" 
        description="Select a project to see details."
      />

      {/* Split view */}
      <box flexGrow={1} flexDirection="row">
        {/* Left panel: Project list */}
        <box
          width={45}
          flexDirection="column"
          border
          borderStyle="single"
          borderColor={theme.goldDim}
        >
          <box
            paddingLeft={1}
            paddingTop={1}
            paddingBottom={1}
            backgroundColor={theme.bgMedium}
          >
            <text>
              <span fg={theme.cyan}>
                <strong>Projects</strong>
              </span>
            </text>
          </box>
          
          <select
            options={projects.map((p) => ({
              name: p.name,
              description: `${p.language} • ${p.commits} commits`,
              value: p.id,
            }))}
            onChange={(index) => setSelectedIndex(index)}
            selectedIndex={selectedIndex}
            focused
            height={16}
            showScrollIndicator
          />
        </box>

        {/* Right panel: Project details */}
        <box
          flexGrow={1}
          flexDirection="column"
          padding={2}
          gap={2}
        >
          {selectedProject && (
            <>
              {/* Project name */}
              <box flexDirection="column" gap={1}>
                <text>
                  <span fg={theme.gold}>
                    <strong>{selectedProject.name}</strong>
                  </span>
                </text>
                <text>
                  <span fg={theme.textSecondary}>{selectedProject.description}</span>
                </text>
              </box>

              {/* Stats */}
              <box flexDirection="row" gap={4}>
                <box flexDirection="column">
                  <text>
                    <span fg={theme.textDim}>Language</span>
                  </text>
                  <text>
                    <span fg={theme.cyan}>
                      <strong>{selectedProject.language}</strong>
                    </span>
                  </text>
                </box>
                <box flexDirection="column">
                  <text>
                    <span fg={theme.textDim}>Commits</span>
                  </text>
                  <text>
                    <span fg={theme.cyan}>
                      <strong>{selectedProject.commits}</strong>
                    </span>
                  </text>
                </box>
                <box flexDirection="column">
                  <text>
                    <span fg={theme.textDim}>Files</span>
                  </text>
                  <text>
                    <span fg={theme.cyan}>
                      <strong>{selectedProject.files}</strong>
                    </span>
                  </text>
                </box>
                <box flexDirection="column">
                  <text>
                    <span fg={theme.textDim}>Updated</span>
                  </text>
                  <text>
                    <span fg={theme.cyan}>
                      <strong>{selectedProject.lastUpdated}</strong>
                    </span>
                  </text>
                </box>
              </box>

              {/* Technologies */}
              <box flexDirection="column" gap={1}>
                <text>
                  <span fg={theme.textDim}>Technologies</span>
                </text>
                <box flexDirection="row" gap={1} flexWrap="wrap">
                  {selectedProject.technologies.map((tech, i) => (
                    <box
                      key={i}
                      backgroundColor={theme.cyanDim}
                      paddingLeft={1}
                      paddingRight={1}
                    >
                      <text>
                        <span fg={theme.textPrimary}>{tech}</span>
                      </text>
                    </box>
                  ))}
                </box>
              </box>
            </>
          )}
        </box>
      </box>
    </box>
  );
}
