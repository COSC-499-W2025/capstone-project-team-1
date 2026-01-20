import { useKeyboard } from "@opentui/react";
import { useEffect, useState } from "react";
import { theme } from "../types";
import { TopBar } from "./TopBar";

interface FileUploadProps {
	onSubmit: (path: string) => void;
	onBack: () => void;
}

// Mock file system data
const mockFileSystem = {
	name: "root",
	type: "dir",
	children: [
		{
			name: "Users",
			type: "dir",
			children: [
				{
					name: "shlok",
					type: "dir",
					children: [
						{
							name: "projects",
							type: "dir",
							children: [
								{ name: "opentui-react", type: "dir" },
								{ name: "capstone-project.zip", type: "file", size: "12 MB" },
								{ name: "personal-site.zip", type: "file", size: "4.5 MB" },
							],
						},
						{ name: "Documents", type: "dir" },
						{
							name: "Downloads",
							type: "dir",
							children: [
								{ name: "resume-data.zip", type: "file", size: "2 MB" },
								{ name: "images.zip", type: "file", size: "150 MB" },
							],
						},
					],
				},
			],
		},
		{ name: "var", type: "dir" },
		{ name: "tmp", type: "dir" },
	],
};

export function FileUpload({ onSubmit, onBack }: FileUploadProps) {
	const [selectedPath, setSelectedPath] = useState(
		"/Users/shlok/projects/capstone-project.zip",
	);

	// Interaction handling would go here - simplified for visual demo

	const handleSubmit = () => {
		onSubmit(selectedPath);
	};

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Step 1"
				title="Select Projects"
				description="Browse for your project zip file"
			/>

			<box flexGrow={1} flexDirection="row" padding={1} gap={1}>
				{/* Left Panel: Directory Tree */}
				<box
					width="60%"
					border
					borderStyle="rounded"
					borderColor={theme.gold}
					flexDirection="column"
					padding={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>File Browser</strong>
						</span>
					</text>
					<text>
						<span fg={theme.textDim}>/Users/shlok/projects/</span>
					</text>
					<box flexDirection="column" marginTop={1}>
						<text> 📁 opentui-react</text>
						<box backgroundColor={theme.cyanDim}>
							<text> 📄 capstone-project.zip</text>
						</box>
						<text> 📄 personal-site.zip</text>
					</box>
				</box>

				{/* Right Panel: Details */}
				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={theme.textDim}
					flexDirection="column"
					padding={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>Details</strong>
						</span>
					</text>
					<box flexDirection="column" marginTop={1} gap={1}>
						<text>
							Name: <span fg={theme.textPrimary}>capstone-project.zip</span>
						</text>
						<text>
							Size: <span fg={theme.textPrimary}>12 MB</span>
						</text>
						<text>
							Type: <span fg={theme.textPrimary}>ZIP Archive</span>
						</text>

						<box
							marginTop={2}
							border
							borderStyle="single"
							borderColor={theme.textDim}
							padding={1}
						>
							<text>Contains:</text>
							<text>• 4 git repositories</text>
							<text>• 1,204 commits</text>
							<text>• TypeScript, Rust</text>
						</box>
					</box>

					<box marginTop={3}>
						<text>
							<span fg={theme.textDim}>Press </span>
							<span fg={theme.cyan}>Enter</span>
							<span fg={theme.textDim}> to select</span>
						</text>
					</box>

					<box
						marginTop={5}
						border
						borderStyle="single"
						borderColor={theme.error}
						paddingLeft={2}
						paddingRight={2}
						paddingTop={1}
						paddingBottom={1}
					>
						<text>
							<span fg={theme.goldDark}>Demo Mode:</span>
							<span fg={theme.textDim}> Press </span>
							<span fg={theme.cyan}>Enter</span>
							<span fg={theme.textDim}> to continue</span>
						</text>
					</box>
				</box>
			</box>
		</box>
	);
}
