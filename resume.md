# Technical Resume

## Professional Summary

A software engineer with 8 projects spanning web APIs, CLI tools, and data analysis libraries, primarily developed in Python, JavaScript, Go, and TypeScript. Built backend systems including a sensor fleet API in Python and a task runner in Go, along with machine learning and data validation tools in Python and TypeScript.

## Technical Skills

Languages: Python, JavaScript, Go, HTML, CSS, Java, TypeScript
Frameworks & Libraries: Express, FastAPI, Data Analysis, Data Validation, Machine Learning, Numerical Computing, Testing
Tools & Infrastructure: Command Line Tools, Resource Management, Context Management
Practices: Technical Writing, TypeScript Typing

## Projects

### go-task-runner
**Language:** Go | **Contribution:** 30%
**Period:** 2020-08-31 to 2021-02-09

A Go-based web API that executes and schedules JSON-defined tasks for homelab workflows with result tracking and validation

- Implemented dry-run mode to allow task execution without side effects, enabling safe testing of workflows
- Added Result structs to map task outputs to API-compatible data structures for consistent response formatting
- Enhanced configuration validation with defined rules to ensure input integrity and prevent invalid task execution
- Integrated JSON result saving functionality to persist task execution outcomes for audit and replay purposes

> Contributed to task execution logic and configuration validation, improving reliability and traceability of scheduled workflows.

### personal-portfolio-site
**Language:** JavaScript | **Contribution:** 100%
**Period:** 2020-12-31 to 2021-09-17

A lightweight static portfolio site that showcases projects, skills, and coursework with minimal setup and accessibility improvements

- Added hero CTA and project grid using the renderProjects function
- Implemented skills section with corresponding renderSkills function and test assertion
- Enabled keyboard navigation to support screen reader accessibility and grid focus order
- Improved visual layout with centered design, hover affordance, and consistent card depth

> Independently built and maintained the entire site, from structure to accessibility, ensuring full functionality and usability across devices and input methods.

### sensor-fleet-backend
**Technologies:** FastAPI, Data Validation, Testing | **Language:** Python | **Contribution:** 43%
**Period:** 2021-06-30 to 2022-01-26

A FastAPI backend service for ingesting and managing IoT sensor readings with health checks, uptime monitoring, and alerting based on threshold conditions

- Implemented the alerts endpoint to return sensor readings exceeding predefined thresholds
- Added the uptime endpoint to provide real-time availability status of the sensor fleet service
- Developed the sensor_average helper function to compute average readings across sensor data

> Contributed to the implementation and testing of key endpoints and utility functions that enhanced monitoring and data analysis capabilities within the sensor fleet system.

### infra-terraform
**Language:** tf | **Contribution:** 30%
**Period:** 2023-06-30 to 2025-11-23

Terraform infrastructure library that defines VPC, subnets, and an app module with S3 logging bucket for study and demo environments

- Added output for the logging bucket to enable service-level visibility and integration with monitoring tools
- Implemented cost center tagging at the local environment level to support financial tracking and accountability
- Introduced stage environment mirroring dev with isolated state to support multi-environment testing and deployment workflows
- Updated documentation to include tfvars examples and version pinning for consistent configuration management

> Contributed to infrastructure configuration by enhancing outputs, environment structure, and documentation to support reliable and traceable environment setup.

### algorithms-toolkit
**Technologies:** Testing | **Language:** Python | **Contribution:** 100%
**Period:** 2021-03-31 to 2021-09-12

A Python CLI tool for interview prep that implements core algorithms like BFS, Dijkstra, and two-sum with built-in testing and usage examples

- Added Dijkstra's shortest path algorithm with support for weighted graphs and path reconstruction
- Implemented a bounded binary search function with target-based lookup and edge case handling
- Built a two-sum helper that identifies pairs in an array summing to a target value
- Wrote unit tests for rotate, reverse, sorted array validation, and two-sum logic to ensure correctness

> Independently built and maintained all core algorithms, tests, and documentation, ensuring full functionality and usability across CLI interactions.

### java-chat-service
**Language:** Java | **Contribution:** 30%
**Period:** 2020-03-31 to 2020-08-22

A lightweight HTTP chat service built with Java that stores and serves chat messages via memory-based storage and key endpoints including /messages, /send, and /health

- Implemented a search messages endpoint to retrieve messages based on author or text content
- Added JSON response format for the /messages endpoint, returning an array of author/text objects
- Developed a message count endpoint to expose the total number of stored messages
- Enhanced message validation to reject requests with empty text input

> Contributed to the implementation of message search and JSON response features, improving message retrieval and API usability for clients.

### campus-navigation-api
**Technologies:** Express, TypeScript | **Language:** TypeScript | **Contribution:** 36%
**Period:** 2022-01-31 to 2022-08-01

A TypeScript Express web API that enables campus pathfinding and schedule-aware routing by providing endpoints for building listings, route planning, and real-time schedule data

- Implemented a schedule endpoint that identifies busy buildings using schedule data to inform route planning
- Added support for fetching a single building via the GET /buildings/:id endpoint
- Developed a safe path routing feature that respects building closures using the shortestPathSafe function
- Enhanced API documentation to include deployment instructions and expanded endpoint descriptions

> Contributed to the implementation of route safety and building-specific data access, improving the accuracy and usability of pathfinding responses for users navigating campus schedules.

### ml-lab-notebooks
**Technologies:** Numerical Computing, Data Analysis, Machine Learning, Testing | **Language:** Python | **Contribution:** 32%
**Period:** 2023-02-28 to 2023-07-28

A Python library for machine learning experiments including linear regression, logistic classification, and dataset preprocessing utilities

- Implemented logistic regression experiment using sklearn for binary classification tasks
- Added rooms_per_area heuristic for dataset preprocessing and feature engineering
- Integrated z-score normalization utility and train/test split functionality for consistent data splitting
- Added MAE metric and corresponding test function to validate model performance

> Contributed to experiment design and data preprocessing features, enhancing reproducibility and model evaluation in the ML lab notebooks project.

## Developer Profile

The developer has a strong foundation in full-stack and library development, with hands-on experience building web APIs in Go, Python, and TypeScript, and contributing to backend services and tooling. They consistently write tests across projects, with full ownership of testing in JavaScript, Python, and Go-based applications, and have delivered robust, well-documented libraries and CLI tools. Their technical range spans backend services, infrastructure automation with Terraform, and algorithmic tooling, demonstrating proficiency across multiple languages and project types.

---
*Generated with qwen3-4b-q4 in 285s*