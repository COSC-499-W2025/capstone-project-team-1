import type { Project, ResumeData, Skill } from "../types";

export const mockProjects: Project[] = [
	{
		id: "go-task-runner",
		name: "Go Task Runner",
		language: "Go",
		description:
			"A lightweight task scheduler and runner built in Go with support for cron-like scheduling, task dependencies, and JSON configuration.",
		technologies: ["Go", "JSON", "CLI", "Concurrency"],
		commits: 24,
		files: 12,
		lastUpdated: "2025-11-23",
	},
	{
		id: "personal-portfolio-site",
		name: "Personal Portfolio Site",
		language: "TypeScript",
		description:
			"A modern portfolio website built with Next.js and Tailwind CSS featuring dark mode, animations, and a blog section.",
		technologies: [
			"TypeScript",
			"Next.js",
			"React",
			"Tailwind CSS",
			"Framer Motion",
		],
		commits: 47,
		files: 34,
		lastUpdated: "2025-11-20",
	},
	{
		id: "sensor-fleet-backend",
		name: "Sensor Fleet Backend",
		language: "Python",
		description:
			"Backend service for IoT sensor fleet management with real-time data ingestion, alerting, and time-series analytics.",
		technologies: [
			"Python",
			"FastAPI",
			"PostgreSQL",
			"TimescaleDB",
			"Redis",
			"Docker",
		],
		commits: 89,
		files: 56,
		lastUpdated: "2025-11-18",
	},
	{
		id: "infra-terraform",
		name: "Infrastructure as Code",
		language: "HCL",
		description:
			"Terraform modules for multi-cloud infrastructure provisioning including AWS, GCP, and Kubernetes clusters.",
		technologies: ["Terraform", "AWS", "GCP", "Kubernetes", "Helm", "CI/CD"],
		commits: 156,
		files: 78,
		lastUpdated: "2025-11-22",
	},
	{
		id: "algorithms-toolkit",
		name: "Algorithms Toolkit",
		language: "Python",
		description:
			"Collection of classic algorithms and data structures with comprehensive tests and performance benchmarks.",
		technologies: [
			"Python",
			"pytest",
			"NumPy",
			"Algorithms",
			"Data Structures",
		],
		commits: 62,
		files: 45,
		lastUpdated: "2025-10-15",
	},
	{
		id: "java-chat-service",
		name: "Java Chat Service",
		language: "Java",
		description:
			"Real-time chat service with WebSocket support, message persistence, and horizontal scaling capabilities.",
		technologies: [
			"Java",
			"Spring Boot",
			"WebSocket",
			"MongoDB",
			"Redis",
			"Docker",
		],
		commits: 134,
		files: 67,
		lastUpdated: "2025-11-10",
	},
	{
		id: "campus-navigation-api",
		name: "Campus Navigation API",
		language: "TypeScript",
		description:
			"REST API for campus navigation with pathfinding algorithms, building info, and accessibility features.",
		technologies: [
			"TypeScript",
			"Node.js",
			"Express",
			"PostgreSQL",
			"PostGIS",
			"GraphQL",
		],
		commits: 78,
		files: 42,
		lastUpdated: "2025-09-28",
	},
	{
		id: "ml-lab-notebooks",
		name: "ML Lab Notebooks",
		language: "Python",
		description:
			"Jupyter notebooks for machine learning experiments including NLP, computer vision, and recommendation systems.",
		technologies: [
			"Python",
			"Jupyter",
			"PyTorch",
			"TensorFlow",
			"scikit-learn",
			"Pandas",
		],
		commits: 43,
		files: 28,
		lastUpdated: "2025-11-05",
	},
];

export const mockSkills: Skill[] = [
	{
		name: "Python",
		level: "expert",
		projects: [
			"sensor-fleet-backend",
			"algorithms-toolkit",
			"ml-lab-notebooks",
		],
	},
	{
		name: "TypeScript",
		level: "advanced",
		projects: ["personal-portfolio-site", "campus-navigation-api"],
	},
	{ name: "Go", level: "intermediate", projects: ["go-task-runner"] },
	{ name: "Java", level: "advanced", projects: ["java-chat-service"] },
	{ name: "Terraform", level: "advanced", projects: ["infra-terraform"] },
	{ name: "React", level: "advanced", projects: ["personal-portfolio-site"] },
	{
		name: "Docker",
		level: "advanced",
		projects: ["sensor-fleet-backend", "java-chat-service"],
	},
	{
		name: "PostgreSQL",
		level: "intermediate",
		projects: ["sensor-fleet-backend", "campus-navigation-api"],
	},
	{ name: "AWS", level: "intermediate", projects: ["infra-terraform"] },
	{
		name: "Machine Learning",
		level: "intermediate",
		projects: ["ml-lab-notebooks"],
	},
];

export const mockResumeData: ResumeData = {
	skills: mockSkills,
	projects: mockProjects,
	summary:
		"Full-stack developer with expertise in Python, TypeScript, and cloud infrastructure. Experienced in building scalable backend services, modern web applications, and DevOps pipelines. Strong foundation in algorithms, data structures, and machine learning.",
};

// Analysis steps for the analysis screen
export const analysisSteps = [
	{ id: "unzip", label: "Extracting archive..." },
	{ id: "detect", label: "Detecting repositories..." },
	{ id: "languages", label: "Analyzing languages..." },
	{ id: "commits", label: "Parsing commit history..." },
	{ id: "deps", label: "Scanning dependencies..." },
	{ id: "skills", label: "Extracting skills..." },
	{ id: "generate", label: "Generating resume..." },
];
