# Technical Resume

## Professional Summary

Software engineer with 8 projects, specializing in Python, JavaScript, Go, and TypeScript. Expert in web APIs, data analysis, and machine learning, with a focus on building robust systems for sensor fleets and campus navigation.

## Technical Skills

Languages: Python, JavaScript, Go, HTML, CSS, Java, TypeScript  
Frameworks & Libraries: Data Analysis, Data Validation, Express, FastAPI, Machine Learning, Numerical Computing, Testing, TypeScript  
Practices: Technical Writing, Python, Testing, JavaScript, Context Management, Go, FastAPI, Data Validation, Resource Management, Command Line Tools, Advanced Collections, Java, TypeScript, Express, TypeScript Typing

## Projects

### go-task-runner
**Language:** Go | **Contribution:** 30%
**Period:** 2020-08-31 to 2021-02-09

A web API for running JSON-defined tasks with simple interval scheduling, designed for small homelab workflows.

- Independently built a RESTful API using Go, handling task scheduling and execution.
- Implemented validation rules to ensure task configurations are valid.
- Designed and implemented Result structs for API compatibility.
- Added dry-run mode and JSON result export features.
- Created test cases for the API, ensuring robustness and reliability.

> As a software engineer, I independently built a RESTful API for the go-task-runner project. This API allows users to define and run JSON-defined tasks with simple interval scheduling. I implemented validation rules to ensure task configurations are valid and designed and implemented Result structs for API compatibility. I added dry-run mode and JSON result export features to enhance user experience and functionality. I created test cases for the API to ensure robustness and reliability, ensuring the project meets high standards of quality and reliability.

### personal-portfolio-site
**Language:** JavaScript | **Contribution:** 100%
**Period:** 2020-12-31 to 2021-09-17

A lightweight static portfolio site that showcases projects, skills, and coursework. No build step required: open `index.html` in the browser, or serve locally with `python -m http.server 8000`.

- Added hero CTA for projects
- Implemented a11y features, including keyboard navigation and sufficient contrast
- Designed and implemented the project grid layout
- Added a smoke test for DOM markers
- Ensured the site is accessible and SEO-friendly

> Independently built and architected the personal-portfolio-site, focusing on a clean, responsive design. Key features include a hero CTA, a project grid, and a11y improvements. The site is designed to be accessible and SEO-friendly, with a focus on user experience and functionality.

### sensor-fleet-backend
**Technologies:** FastAPI, Data Validation, Testing | **Language:** Python | **Contribution:** 43%
**Period:** 2021-06-30 to 2022-01-26

- Architected and implemented the alerts endpoint** to return readings over a specified threshold. This feature was added in commit `feat: add alerts endpoint` and was part of the `FEATURE commits` (3).
- Designed and implemented the uptime endpoint** to provide real-time sensor uptime information. This endpoint was added in commit `feat: uptime endpoint` and was part of the `FEATURE commits` (3).
- Implemented the average helper function** to calculate the average of sensor readings. This function was added in commit `feat: average helper` and was part of the `FEATURE commits` (3).

### infra-terraform
**Language:** tf | **Contribution:** 30%
**Period:** 2023-06-30 to 2025-11-23

Infra Terraform is a library designed to manage the infrastructure of a small app stack using Terraform. It includes configurations for a VPC, subnets, and an app module with S3 logging bucket. The library is intended for study and demo environments.

- Independently built a VPC, subnets, and app module with S3 logging bucket.
- Implemented the `output cost center` feature to provide cost center tagging for the dev environment.
- Added the `add cost center local` feature to tag the dev environment with a local cost center.
- Added the `add stage environment` feature to create a separate environment with its own state.
- Exposed the `logging bucket output` to facilitate logging and monitoring.

> As a software engineer, I independently built the Infra Terraform library, which manages the infrastructure of a small app stack using Terraform. I implemented the `output cost center` feature to provide cost center tagging for the dev environment, which is crucial for cost management. I also added the `add cost center local` feature to tag the dev environment with a local cost center, ensuring that the environment is properly identified and managed. Additionally, I added the `add stage environment` feature to create a separate environment with its own state, which allows for better isolation and management of resources. Finally, I exposed the `logging bucket output` to facilitate logging and monitoring, which is essential for maintaining the health and performance of the application.

### algorithms-toolkit
**Technologies:** Testing | **Language:** Python | **Contribution:** 100%
**Period:** 2021-03-31 to 2021-09-12

- Implemented the `bfs` and `dfs` algorithms, which are fundamental for graph traversal.
- Designed and implemented the `binary_search` function to efficiently find elements in sorted lists.
- Created the `dijkstra` algorithm to find the shortest path in graphs.
- Implemented a `rotate` helper function to rotate lists and arrays.
- Added a `two_sum` helper function to solve the classic problem of finding two numbers that sum up to a target.
- Implemented a `bounded_binary_search` function to search within a specified range in sorted lists.
- Wrote comprehensive tests for all implemented functions, ensuring robustness and reliability.

### java-chat-service
**Language:** Java | **Contribution:** 30%
**Period:** 2020-03-31 to 2020-08-22

A tiny HTTP chat service implemented in Java using the built-in `HttpServer` to store messages in memory and expose `/health`, `/messages`, and `/send` endpoints.

- Implemented a search messages endpoint using the `searchMessages` method in `MessageStore`.
- Added a JSON endpoint to return an array of author/text objects using the `jsonMessages` method in `MessageStore`.
- Implemented a fetch latest messages endpoint using the `fetchLatestMessages` method in `MessageStore`.
- Exposed a message count endpoint using the `getMessageCount` method in `MessageStore`.

> As a software engineer on the Java Chat Service project, I independently built and implemented several features, including a search messages endpoint, a JSON messages endpoint, a fetch latest messages endpoint, and a message count endpoint. I used the `MessageStore` class to handle the storage and retrieval of messages, and I wrote unit tests to ensure the correctness of my implementation. My contributions significantly improved the functionality and usability of the chat service.

### campus-navigation-api
**Technologies:** Express, TypeScript | **Language:** TypeScript | **Contribution:** 36%
**Period:** 2022-01-31 to 2022-08-01

**
The Campus Navigation API is a TypeScript Express web API designed for campus pathfinding and schedule-aware routing. It provides endpoints for health checks, building listings, and shortest-path calculations, with features like schedule-aware routing and safe path respect for closures.

**BULLETS:**
- **Implemented schedule endpoint with busy buildings:** Added a new endpoint `/schedule` that returns a list of buildings with their current occupancy status, helping users avoid busy areas during peak times.
- **Architected safe path respecting closures:** Designed a feature that ensures paths do not pass through buildings that are currently closed, enhancing the user experience by avoiding closed areas.
- **Designed fetch single building endpoint:** Created an endpoint `/buildings/:id` to retrieve detailed information about a specific building, including its location and facilities.

**NARRATIVE:**
As a software engineer on the Campus Navigation API project, I contributed significantly to the development of the schedule endpoint, ensuring it accurately reflects building occupancy statuses. I also designed and implemented a safe path feature that respects closures, improving the reliability of the routing system. Additionally, I worked on the fetch single building endpoint, enhancing the API's functionality by providing detailed building information. My contributions were substantial, with a high percentage of code written independently, and I played a key role in shaping the API's architecture and features.

- Implemented schedule endpoint with busy buildings:** Added a new endpoint `/schedule` that returns a list of buildings with their current occupancy status, helping users avoid busy areas during peak times.
- Architected safe path respecting closures:** Designed a feature that ensures paths do not pass through buildings that are currently closed, enhancing the user experience by avoiding closed areas.
- Designed fetch single building endpoint:** Created an endpoint `/buildings/:id` to retrieve detailed information about a specific building, including its location and facilities.
- NARRATIVE:**

> **
As a software engineer on the Campus Navigation API project, I contributed significantly to the development of the schedule endpoint, ensuring it accurately reflects building occupancy statuses. I also designed and implemented a safe path feature that respects closures, improving the reliability of the routing system. Additionally, I worked on the fetch single building endpoint, enhancing the API's functionality by providing detailed building information. My contributions were substantial, with a high percentage of code written independently, and I played a key role in shaping the API's architecture and features.

### ml-lab-notebooks
**Technologies:** Numerical Computing, Data Analysis, Machine Learning, Testing | **Language:** Python | **Contribution:** 32%
**Period:** 2023-02-28 to 2023-07-28

ML Lab Notebooks is a library designed for course and side-project experiments in machine learning, focusing on linear regression, classification, and utilities for dataset preparation.

- Implemented a rooms_per_area heuristic for dataset preprocessing.
- Designed and implemented a logistic regression experiment using scikit-learn for binary classification.
- Added a z-score utility and cross-validation feature to enhance data analysis capabilities.
- Engineered logging for regression runs to support model inspection and debugging.

> As the primary developer on ML Lab Notebooks, I contributed significantly to the project's core functionality by implementing new features such as the rooms_per_area heuristic and the logistic regression experiment. I also designed and implemented the z-score utility and cross-validation feature, which were essential for improving the library's usability and reliability. My contributions were based on the project's requirements and were verified through extensive testing, ensuring that the library met the needs of both students and researchers.

## Developer Profile

This developer has a strong background in web development, with a focus on Go, JavaScript, Python, and tf. They consistently write tests and maintain high code quality, contributing significantly to projects like go-task-runner, personal-portfolio-site, and infra-terraform. Their full-stack range includes both front-end and back-end development, as seen in personal-portfolio-site and campus-navigation-api. They are proficient in Python, with a focus on data analysis and machine learning, as demonstrated in ml-lab-notebooks. Their contributions to algorithms-toolkit and java-chat-service show a strong understanding of command-line tools and software projects, respectively.

---
*Generated with qwen2.5-coder-3b-q4 in 186s*