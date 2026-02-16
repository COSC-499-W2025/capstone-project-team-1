Prompt: baseline
Model                      Secs Δ vs ChatGPT (s) Mirage (lower is better)     Grounding (higher is better) Redundancy (lower is better)
------------------------ ------ ---------------- ---------------------------- ---------------------------- ----------------------------
gpt-5-nano                13.09            +0.00 0.30 ####-------- 0.62 #######----- 0.20 ##----------
llama3.2:1b                4.19            -8.91 0.16 ##---------- 0.79 #########--- 0.00 ------------
llama3.2:3b                5.45            -7.64 0.18 ##---------- 0.76 #########--- 0.00 ------------
llama3.1:8b               11.03            -2.06 0.27 ###--------- 0.63 ########---- 0.04 ------------
gemma3:4b                 15.03            +1.94 0.43 #####------- 0.46 ######------ 0.09 #-----------
gemma3:12b                30.56           +17.47 0.48 ######------ 0.37 ####-------- 0.07 #-----------
gemma2:2b                  9.61            -3.48 0.39 #####------- 0.49 ######------ 0.08 #-----------
gemma2:9b                 21.98            +8.89 0.39 #####------- 0.48 ######------ 0.17 ##----------
gemma:7b                  17.83            +4.73 0.14 ##---------- 0.84 ##########-- 0.13 ##----------
qwen2.5:0.5b               3.88            -9.22 0.15 ##---------- 0.80 ##########-- 0.00 ------------
qwen2.5:1.5b               6.41            -6.69 0.22 ###--------- 0.74 #########--- 0.04 ------------
qwen2.5:3b                 7.26            -5.83 0.28 ###--------- 0.63 ########---- 0.04 ------------
qwen2.5:7b                17.03            +3.94 0.41 #####------- 0.45 #####------- 0.07 #-----------
qwen2.5:14b               47.50           +34.41 0.40 #####------- 0.50 ######------ 0.05 #-----------
qwen3:4b                  12.02            -1.08 0.28 ###--------- 0.64 ########---- 0.20 ##----------
qwen3:8b                  21.08            +7.98 0.29 ###--------- 0.63 ########---- 0.13 ##----------
qwen3:14b                 44.27           +31.17 0.39 #####------- 0.51 ######------ 0.00 ------------
deepseek-r1:1.5b           9.05            -4.05 0.19 ##---------- 0.74 #########--- 0.26 ###---------
deepseek-r1:7b            18.92            +5.83 0.37 ####-------- 0.54 ######------ 0.00 ------------
deepseek-r1:14b           41.17           +28.08 0.42 #####------- 0.48 ######------ 0.03 ------------
phi3:3.8b                 18.45            +5.36 0.49 ######------ 0.39 #####------- 0.11 #-----------
phi3:14b                  66.39           +53.30 0.45 #####------- 0.42 #####------- 0.08 #-----------
phi3.5:3.8b               29.59           +16.50 0.47 ######------ 0.38 #####------- 0.09 #-----------
phi4:14b                  44.28           +31.19 0.41 #####------- 0.49 ######------ 0.06 #-----------
phi4-mini:3.8b            11.84            -1.25 0.42 #####------- 0.50 ######------ 0.03 ------------
phi4-mini-reasoning:3.8b  13.11            +0.02 0.31 ####-------- 0.61 #######----- 0.08 #-----------
mistral:7b                19.09            +6.00 0.21 ##---------- 0.73 #########--- 0.07 #-----------
mistral-nemo:12b          34.23           +21.14 0.41 #####------- 0.49 ######------ 0.00 ------------
mixtral:8x7b             102.03           +88.94 0.27 ###--------- 0.67 ########---- 0.11 #-----------
granite3-dense:2b         10.75            -2.34 0.18 ##---------- 0.73 #########--- 0.10 #-----------
granite3-dense:8b         18.12            +5.03 0.18 ##---------- 0.76 #########--- 0.19 ##----------
granite3.3:2b              7.86            -5.23 0.37 ####-------- 0.52 ######------ 0.15 ##----------
granite3.3:8b             27.09           +14.00 0.27 ###--------- 0.65 ########---- 0.10 #-----------
granite4:3b               15.81            +2.72 0.26 ###--------- 0.66 ########---- 0.12 #-----------
deepseek-coder:1.3b        5.80            -7.30 0.41 #####------- 0.47 ######------ 0.00 ------------
deepseek-coder:6.7b       19.14            +6.05 0.21 ##---------- 0.72 #########--- 0.03 ------------
starcoder2:3b              9.88            -3.22 0.02 ------------ 0.97 ############ 0.24 ###---------
starcoder2:7b             15.66            +2.56 0.05 #----------- 0.96 ############ 0.00 ------------
codegemma:7b              22.97            +9.88 0.11 #----------- 0.86 ##########-- 0.13 ##----------
codellama:7b              18.91            +5.81 0.02 ------------ 0.97 ############ 0.05 #-----------
tinyllama:1.1b             4.47            -8.63 0.25 ###--------- 0.66 ########---- 0.10 #-----------
smollm2:1.7b              13.56            +0.47 0.03 ------------ 0.97 ############ 0.18 ##----------
falcon3:3b                 8.14            -4.95 0.38 #####------- 0.52 ######------ 0.11 #-----------
falcon3:7b                19.94            +6.84 0.29 ###--------- 0.61 #######----- 0.03 ------------
olmo2:7b                  18.94            +5.84 0.35 ####-------- 0.56 #######----- 0.00 ------------
openchat:7b               15.19            +2.09 0.10 #----------- 0.90 ###########- 0.15 ##----------
neural-chat:7b            16.12            +3.03 0.21 ###--------- 0.72 #########--- 0.07 #-----------
starling-lm:7b            15.52            +2.42 0.19 ##---------- 0.76 #########--- 0.14 ##----------
dolphin-mistral:7b        18.45            +5.36 0.08 #----------- 0.90 ###########- 0.04 ------------
zephyr:7b                 17.97            +4.87 0.02 ------------ 0.98 ############ 0.12 #-----------
Top 3 responses:
#1 starcoder2:7b
Score: 0.970
Mirage: 0.05
Grounding: 0.96
Redundancy: 0.00
Response:
{"project_name": "Campus Resource Tracker", "one_liner": "Web app to help students log study spaces, equipment loans, and lab availability.", "highlights": ["Added caching to reduce API latency and rate limits.", "Improved error messages and validation for booking conflicts."], "skills": ["Python", "FastAPI", "SQLAlchemy", "D3"]}
---
#2 codellama:7b
Score: 0.966
Mirage: 0.02
Grounding: 0.97
Redundancy: 0.05
Response:
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app to help students log study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Added caching to reduce API latency and rate limits.",
    "Added audit logging for reservation updates.",
    "Improved error messages and validation for booking conflicts."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js"
  ]
}
---
#3 zephyr:7b
Score: 0.947
Mirage: 0.02
Grounding: 0.98
Redundancy: 0.12
Response:
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app to help students log study spaces, equipment loans, and lab availability.",
  "highlights": [
    "FastAPI endpoints for spaces, availability, and reservations.",
    "SQLAlchemy models for spaces, reservations, and users.",
    "React dashboard with filters, calendar view, and alerts.",
    "D3-based chart for weekly utilization.",
    "Caching to reduce API latency and rate limits.",
    "Audit logging for reservation updates."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js"
  ]
}
---
Invalid JSON outputs: deepseek-r1:8b, codegemma:2b
Errored models: stable-code:3b (llama runner process has terminated: cudaMalloc failed: out of memory (status code: 500))
All responses:
gpt-5-nano (valid JSON)
{
  "highlights": [
    "Implemented a FastAPI backend exposing endpoints for spaces, availability, and reservations with SQLAlchemy models for spaces, reservations, and users.",
    "Added TTL-based caching and retry logic for live availability to reduce latency and API rate limits.",
    "Implemented audit logging for reservation updates to improve traceability and accountability.",
    "Enhanced booking validation and error messaging to prevent conflicts and provide clear user feedback.",
    "Developed a React dashboard with filters, calendar view, and alerts, plus a D3-based weekly utilization chart; included UI/API tests for availability and dashboard behavior."
  ],
  "one_liner": "Full-stack Campus Resource Tracker: a web app to log study spaces, equipment loans, and lab availability with caching, auditing, and robust error handling.",
  "project_name": "Campus Resource Tracker",
  "skills": [
    "Python",
    "FastAPI",
    "SQLAlchemy",
    "Caching (TTL)",
    "Retry logic",
    "Audit logging",
    "Error handling",
    "React",
    "TypeScript",
    "D3",
    "UI testing",
    "pytest"
  ]
}
---
llama3.2:1b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "A web app to help students manage study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Improved caching with reduced API latency and rate limits",
    "Added audit logging for reservation updates",
    "Enhanced error messages and validation for booking conflicts"
  ],
  "skills": ["FastAPI", "SQLAlchemy", "React", "D3.js"]
}
---
llama3.2:3b (valid JSON)
{"project_name": "Campus Resource Tracker", "one_liner": "Developed a web app to streamline student resource utilization, incorporating caching and audit logging.", "highlights": ["Implemented caching to reduce API latency and rate limits.", "Added audit logging for reservation updates.", "Improved error messages and validation for booking conflicts."], "skills": ["FastAPI", "SQLAlchemy", "D3.js", "React", "Python"]}
---
llama3.1:8b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web app to streamline student resource management, reducing API latency through caching and improving user experience with enhanced error handling.",
  "highlights": [
    "Implemented caching to reduce API latency and rate limits",
    "Added audit logging for reservation updates",
    "Improved error messages and validation for booking conflicts"
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js",
    "Caching with TTL and retries"
  ]
}
---
gemma3:4b (valid JSON)
{"project_name": "Campus Resource Tracker", "one_liner": "Developed a robust web application utilizing React, FastAPI, and SQLAlchemy to streamline campus resource management and enhance student efficiency.", "highlights": [
  "Implemented caching with TTL and retries to significantly reduce API latency and mitigate rate limits.",
  "Designed and developed a user-friendly React dashboard with interactive filters and a calendar view.",
  "Integrated D3-based charting to visualize weekly resource utilization trends.",
  "Implemented audit logging for reservation updates, ensuring data integrity and accountability."
], "skills": [
  "React",
  "FastAPI",
  "SQLAlchemy",
  "D3.js",
  "Caching",
  "API Development",
  "Database Design",
  "UI Development"
]}
---
gemma3:12b (valid JSON)
{"project_name": "Campus Resource Tracker", "one_liner": "Developed a web application utilizing FastAPI, SQLAlchemy, React, and D3 to provide students with real-time information and booking capabilities for campus resources.", "highlights": [
  "Implemented caching mechanisms to reduce API latency and improve performance, demonstrating proficiency in optimization techniques.",
  "Designed and developed RESTful API endpoints using FastAPI, ensuring efficient data management and accessibility.",
  "Built a dynamic React dashboard with interactive visualizations (D3) to enhance user experience and data comprehension.",
  "Integrated audit logging for reservation updates, contributing to improved system accountability and traceability.",
  "Enhanced error handling and validation to provide informative feedback to users and prevent booking conflicts."
], "skills": ["FastAPI", "SQLAlchemy", "React", "D3.js", "REST API", "Caching", "Testing", "TypeScript"]}
---
gemma2:2b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web application to improve student access to study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Implemented caching to reduce API latency and mitigate rate limits.",
    "Introduced audit logging for reservation updates to enhance accountability.",
    "Improved error messages and validation for booking conflicts to provide clearer user feedback."
  ],
  "skills": [
    "Web Development",
    "API Design",
    "Data Modeling",
    "Caching Techniques",
    "Frontend Development (React)",
    "Backend Development (Python)"
  ]
}
---
gemma2:9b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web application to streamline campus resource management for students.",
  "highlights": [
    "Built a full-stack web application using FastAPI, React, and SQLAlchemy to track study spaces, equipment loans, and lab availability.",
    "Implemented caching strategies with TTL and retries to optimize API performance and handle rate limits.",
    "Integrated D3.js for interactive data visualization, showcasing weekly resource utilization trends."
  ],
  "skills": [
    "FastAPI",
    "React",
    "SQLAlchemy",
    "D3.js",
    "Caching",
    "API Development",
    "Data Visualization"
  ]
}
---
gemma:7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app to streamline resource booking and availability tracking for students.",
  "highlights": [
    "Implemented caching to reduce API latency and rate limits.",
    "Added audit logging for reservation updates.",
    "Improved error handling and validation for booking conflicts."
  ],
  "skills": [
    "FastAPI",
    "React",
    "D3",
    "SQLAlchemy",
    "Caching",
    "Audit Logging"
  ]
}
---
qwen2.5:0.5b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "A web app that helps students manage study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Web app to help students log study spaces, equipment loans, and lab availability.",
    "Caching live availability with TTL and retries for faster API responses.",
    "Audit logging for reservation updates.",
    "Improved error messages and validation for booking conflicts."
  ],
  "skills": [
    "Python",
    "Django",
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js"
  ]
}
---
qwen2.5:1.5b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "A web app that helps students manage study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Implemented caching to reduce API latency and rate limits.",
    "Added audit logging for reservation updates.",
    "Improved error messages and validation for booking conflicts."
  ],
  "skills": [
    "Web Development",
    "API Design",
    "Database Management",
    "React UI Development",
    "FastAPI Backend"
  ]
}
---
qwen2.5:3b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web application using FastAPI, SQLAlchemy, React, and D3.js to manage study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Implemented caching for API endpoints to reduce latency and rate limits.",
    "Added audit logging for reservation updates to ensure accountability.",
    "Improved error messages and validation for booking conflicts to enhance user experience.",
    "Created a React dashboard with filters, calendar view, and alerts for easy management of resources.",
    "Developed a D3-based usage chart component to visualize weekly resource utilization."
  ],
  "skills": [
    "Python (FastAPI, SQLAlchemy)",
    "React",
    "D3.js",
    "SQLAlchemy",
    "Web development"
  ]
}
---
qwen2.5:7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web application using FastAPI, SQLAlchemy, and React to enhance campus resource management.",
  "highlights": [
    "Designed and implemented API endpoints with FastAPI for efficient data handling.",
    "Integrated caching mechanisms to improve performance and reduce latency.",
    "Created interactive dashboards and charts using D3.js for real-time utilization tracking."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "Caching",
    "Error Handling",
    "Testing"
  ]
}
---
qwen2.5:14b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web application to manage campus resource availability, reservations, and usage analytics.",
  "highlights": [
    "Implemented FastAPI endpoints for efficient data retrieval and management of study spaces and equipment loans.",
    "Integrated caching mechanisms to enhance API performance and reduce rate limits.",
    "Created a user-friendly React dashboard with D3-based charts for visualizing weekly utilization trends.",
    "Enhanced system reliability by adding audit logging and improved error handling."
  ],
  "skills": [
    "FastAPI",
    "React",
    "D3.js",
    "SQLAlchemy",
    "Python",
    "JavaScript"
  ]
}
---
qwen3:4b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web application for students to log study spaces, equipment loans, and lab availability with real-time tracking and analytics.",
  "highlights": [
    "Developed FastAPI backend with SQLAlchemy models to manage student resource reservations and availability.",
    "Implemented caching with TTL and retry mechanisms to reduce API latency by 40% and handle rate limits.",
    "Created React dashboard with D3.js for weekly utilization charts and real-time alerts for resource conflicts.",
    "Added audit logging and improved error handling to ensure data integrity during reservation updates."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js",
    "Caching",
    "Audit Logging",
    "Error Handling"
  ]
}
---
qwen3:8b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web app to help students track study spaces, equipment loans, and lab availability with real-time updates and caching.",
  "highlights": [
    "Built FastAPI endpoints for managing space availability and reservations.",
    "Implemented caching with TTL and retries to reduce API latency and rate limits.",
    "Created React dashboard with D3 charts for visualizing resource utilization.",
    "Added audit logging and improved error handling for reservation updates.",
    "Designed SQLAlchemy models for scalable data storage and user management."
  ],
  "skills": [
    "FastAPI",
    "React",
    "D3.js",
    "SQLAlchemy",
    "Caching",
    "Error Handling",
    "Database Design"
  ]
}
---
qwen3:14b (valid JSON)
{"project_name": "Campus Resource Tracker", "one_liner": "Developed a web application to manage campus study spaces, equipment loans, and lab availability with FastAPI, React, and PostgreSQL.", "highlights": ["Reduced API latency by 40% through caching and retry mechanisms", "Implemented audit logging for reservation updates", "Enhanced user experience with interactive dashboard and utilization charts"], "skills": ["FastAPI", "React", "PostgreSQL", "D3.js", "SQLAlchemy", "Testing (Pytest, Jest)"]}
---
deepseek-r1:1.5b (valid JSON)
{"project_name": "Campus Resource Tracker", "one_liner": "A web-based resource tracking system that helps students manage study spaces, equipment loans, and lab availability across the campus.", "highlights": [
  "Web app to help students log study spaces, equipment loans, and lab availability.",
  "Caching live availability with TTL and retries.",
  "API endpoints for spaces, availability, and reservations.",
  "SQL models for spaces, reservations, and users.",
  "Real-time dashboard with filters and calendar view.",
  "Error handling and logging for booking conflicts.",
  "Web app to help students log study spaces, equipment loans, and lab availability."
], "skills": ["web development", "database management", "api programming", "technical skills"]}
---
deepseek-r1:7b (valid JSON)
{

"project_name": "Campus Resource Tracker",
"one_liner": "Web app tracks study spaces, equipment loans, and lab availability with real-time data and caching.",
"highlights": [
  "Developed a web application to help students manage campus resources efficiently.",
  "Implemented caching mechanisms to reduce API latency and improve user experience.",
  "Added audit logging for tracking resource reservations."
],
"skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "React", "D3.js"]
}
---
deepseek-r1:8b (invalid JSON)
{

    "project_name": "Project Name", "one_liner"
    : "one " ,"highlights" :
    [ "skills" ],

    "skills" :

  [ "]}</think><think>ожожажажаю, я не поня не понимаю русь русский, я ойыдякке, ар. ожажажаю не понь ой ожажажажажажажажажажажажажажажажажажажажажажажажажажажажажажажаж
---
deepseek-r1:14b (valid JSON)
{ "project_name": "Campus Resource Tracker", "one_liner": "Web application that helps students track study spaces, equipment loans, and lab availability with real-time data and reservation capabilities.", "highlights": ["Developed a web app to manage campus resources efficiently", "Implemented FastAPI endpoints for resource management", "Integrated caching mechanism to enhance API performance", "Created user-friendly dashboard with D3 visualizations", "Added comprehensive error handling and logging"], "skills": ["Python", "FastAPI", "React", "TypeScript", "SQLAlchemy", "D3.js", "Testing"] }
---
phi3:3.8b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a fast, efficient web app to optimize campus resource utilization with caching, audit logging, improved user experience.",
  "highlights": [
    "Implemented FastAPI endpoints for real-time tracking of study spaces and equipment loans using Python",
    "Introduced SQLAlchin database models in Django for robust data management",
    "Designed a React dashboard with D3 charts to visualize weekly resource utilization, enhancing user interaction",
    "Enhanced error handling by improving messages and validation rules"
  ],
  "skills": [
    "Python programming (FastAPI)",
    "React.js for frontend development",
    "D3.js for data visualization",
    "SQLAlchemy ORM for database management",
    "Caching mechanisms and TTL implementation in Python"
  ]
}
---
phi3:14b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web application to streamline campus resource management, enhancing student accessibility through efficient tracking of study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Designed and implemented FastAPI endpoints for managing resources with robust error handling and validation mechanisms.",
    "Integrated caching to optimize API performance and adhere to rate limits.",
    "Implemented audit logging features for enhanced security and accountability in reservation updates.",
    "Created a user-friendly React dashboard featuring filters, calendar view, and alerts for real-time resource utilization tracking.",
    "Utilized D3.js to visualize weekly space usage with an interactive chart."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy ORM",
    "React and React components",
    "D3.js for data visualization",
    "Test-driven development"
  ]
}
---
phi3.5:3.8b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a comprehensive web application to efficiently manage campus resource logistics, enhancing student convenience with live tracking of study spaces and equipment availability.",
  "highlights": [
    "Implemented caching mechanism using TTL in `src/services/availability.py` to reduce API latency and adhere to rate limits, improving user experience by providing faster access to resource information.",
    "Introduced audit logging for reservation updates within the application, ensuring transparency and accountability of space usage management.",
    "Enhanced error handling with better messages in `tests/api/test_availability.py` and `tests/ui/test_dashboard.py`, covering filtering behavior and empty states to ensure robust user interaction feedback.",
    "Utilized D3 for a dynamic, interactive weekly utilization chart (`src/ui/components/UsageChart.tsx`) that visually represents resource usage patterns."
  ],
  "skills": [
    "Web development with FastAPI",
    "React UI Development using TypeScript in `src/ui/Dashboard.tsx` and components like UsageChart.",
    "SQLAlch extrusion for database interactions via models defined in `src/db/models.py`.",
    "Implemented caching strategies to optimize API performance.",
    "Error handling and testing with pytest framework, including validation of booking conflicts."
  ]
}
---
phi4:14b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a comprehensive web application to streamline the management of study spaces, equipment loans, and lab availability for students.",
  "highlights": [
    "Implemented FastAPI endpoints to efficiently manage space reservations and availability data.",
    "Enhanced system performance by integrating caching mechanisms with TTL and retry logic.",
    "Designed a user-friendly React dashboard featuring filters, calendar views, and real-time alerts.",
    "Developed D3-based utilization charts for insightful weekly usage analytics.",
    "Improved error handling and validation processes to minimize booking conflicts."
  ],
  "skills": [
    "FastAPI",
    "React",
    "D3.js",
    "SQLAlchemy",
    "Caching strategies",
    "Audit logging"
  ]
}
---
phi4-mini:3.8b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web app with FastAPI, SQLAlchemy, React, D3.js that helps students manage study spaces, equipment loans, lab availability, reservations while enhancing performance through caching.",
  "highlights": [
    "Implemented API endpoints for efficient resource management and reservation handling using FastAPI",
    "Integrated live data caching to improve application responsiveness and reduce rate limits",
    "Enhanced user experience with a React-based dashboard featuring filters, calendar view, alerts"
  ],
  "skills": ["FastAPI", "SQLAlchemy", "React.js", "D3.js"]
}
---
phi4-mini-reasoning:3.8b (valid JSON)
{"project_name":"Campus Resource Tracker","one_liner":"Developed a web app to streamline tracking of study spaces, equipment loans, and lab availability.","highlights":["Implemented FastAPI endpoints for efficient resource management","Added caching with TTL and retry mechanisms to optimize performance","Enhanced error handling and audit logging for reservations"],"skills":["Web development","FastAPI","Caching strategies","SQLAlchemy","React","D3 visualization","Testing"]}
---
mistral:7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web app to manage study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Implemented FastAPI endpoints for spaces, availability, and reservations",
    "Created React dashboard with filters, calendar view, and alerts",
    "Developed D3-based chart for weekly utilization",
    "Added caching to reduce API latency and rate limits"
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "TypeScript",
    "D3.js",
    "Pytest"
  ]
}
---
mistral-nemo:12b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a responsive web app using FastAPI, SQLAlchemy, and React to manage campus resources efficiently.",
  "highlights": [
    "Implemented caching with TTL and retries to reduce API latency by 75%",
    "Introduced audit logging for reservation updates, enhancing system accountability",
    "Enhanced user experience through improved error messages and conflict validation during bookings"
  ],
  "skills": ["FastAPI", "SQLAlchemy", "React", "D3.js", "Python", "Git"]
}
---
mixtral:8x7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web app to help students track study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Implemented FastAPI endpoints for managing spaces, availability, and reservations.",
    "Utilized D3 and React to create a weekly utilization chart and user-friendly dashboard.",
    "Improved system performance by adding caching with TTL and retries.",
    "Enhanced error handling and validation for booking conflicts and API responses."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3",
    "TTL Caching",
    "Audit Logging"
  ]
}
---
granite3-dense:2b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app for tracking study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Developed a web application using React, Django, and FastAPI to manage campus resources.",
    "Implemented caching with TTL and retries in the API to reduce latency and rate limits.",
    "Added audit logging for reservation updates and improved error messages for booking conflicts."
  ],
  "skills": [
    "React",
    "Django",
    "FastAPI",
    "SQLAlchemy",
    "D3.js",
    "Testing"
  ]
}
---
granite3-dense:8b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app helping students manage study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Developed a FastAPI web app with SQLAlchemy models for spaces, reservations, and users",
    "Implemented caching to reduce API latency and rate limits",
    "Added audit logging for reservation updates",
    "Improved error messages and validation for booking conflicts",
    "Created a React dashboard with filters, calendar view, and alerts"
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js",
    "Caching mechanisms",
    "Audit logging",
    "Error handling and validation"
  ]
}
---
granite3.3:2b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "A web application using FastAPI, SQLAlchemy, React, and D3.js to help students manage study spaces, equipment loans, and lab availability with caching, audit logging, and enhanced error handling.",
  "highlights": [
    "Developed a web application for tracking campus resources using FastAPI for API endpoints and SQLAlchemy for database management.",
    "Implemented caching in routes.py to reduce latency and handle rate limits, enhancing user experience.",
    "Integrated availability checks with ttl and retries in availability.py, ensuring real-time data accuracy.",
    "Designed a responsive UI dashboard using React, providing filters, calendar view, and alerts for users.",
    "Utilized D3.js to create an interactive utilization chart, offering insights into resource usage patterns.",
    "Enhanced error messages and validation for booking conflicts in tests/api/test_availability.py and tests/ui/test_dashboard.py, improving system reliability."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js",
    "Caching (TTL, retries)",
    "Audit logging",
    "Error handling and validation",
    "Database management",
    "User interface design"
  ]
}
---
granite3.3:8b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web application using FastAPI, React, and SQLAlchemy to help students manage study spaces, equipment loans, and lab availability with caching and audit logging.",
  "highlights": [
    "Implemented FastAPI endpoints for managing spaces, availability, and reservations.",
    "Designed SQLAlchemy models for efficient data handling of spaces, reservations, and users.",
    "Created a React dashboard with filters, calendar view, and alerts for user-friendly interaction.",
    "Developed a D3-based chart for visualizing weekly utilization of resources.",
    "Enhanced system performance by adding caching to reduce API latency and rate limits."
  ],
  "skills": [
    "FastAPI",
    "React",
    "SQLAlchemy",
    "D3.js",
    "Caching mechanisms",
    "Audit logging"
  ]
}
---
granite4:3b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "A web app enabling students to log study spaces, equipment loans, and lab availability with improved caching and error handling.",
  "highlights": [
    "Developed a FastAPI backend for managing resources and reservations.",
    "Implemented caching mechanisms using TTL and retries to reduce API latency and rate limits.",
    "Enhanced user experience with an interactive React dashboard featuring filters, calendar view, and alerts.",
    "Created D3-based charts for visualizing weekly utilization of study spaces."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js",
    "Caching (TTL, retries)",
    "Audit Logging"
  ]
}
---
deepseek-coder:1.3b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app that helps students log study spaces, equipment loans, lab availability.",
  "highlights": [
    "Integrated calendar view with filtering and alerting capabilities for different time slots. ",
    "Implemented caching to reduce API latency by storing live data in a cache using TTL (Time-To-Live).",
    "Incorporated audit logging system, tracking changes made on reservations." ],
   "skills": [
     "FastAPI for backend services.",
     "SQLAlchemy ORM as the database layer. ",
     "ReactJS with D3 library to create interactive charts and dashboards" ]
}
---
deepseek-coder:6.7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app developed using FastAPI, SQLAlchemy, React to track study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Developed a web application with FastAPI endpoints for managing resources on campus.",
    "Implemented caching mechanisms to reduce API latency and rate limits.",
    "Integrated audit logging for reservation updates.",
    "Enhanced error messages and validation for booking conflicts."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js"
  ]
}
---
starcoder2:3b (valid JSON)
{"project_name": "Campus Resource Tracker", "one_liner": "Web app to help students log study spaces, equipment loans, and lab availability.", "highlights": ["FastAPI endpoints for spaces, reservations, and users.", "Caching live availability with TTL and retries.", "SQLAlchemy models for spaces, reservations, and users.", "React dashboard with filters, calendar view, and alerts."], "skills": ["Python", "FastAPI", "SQLAlchemy", "React"]}
---
starcoder2:7b (valid JSON)
{"project_name": "Campus Resource Tracker", "one_liner": "Web app to help students log study spaces, equipment loans, and lab availability.", "highlights": ["Added caching to reduce API latency and rate limits.", "Improved error messages and validation for booking conflicts."], "skills": ["Python", "FastAPI", "SQLAlchemy", "D3"]}
---
codegemma:2b (invalid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app to help students log study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Designed a RESTful API for spaces, reservations, and users.",
    "Implemented caching for API responses and rate limits.",
    "Implemented audit logging for reservation updates."
  ],
  "skills": [
    "Python",
    "FastAPI",
    "SQLAlchemy",
    "D
---
codegemma:7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web app to help students manage study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Implemented caching to reduce API latency and rate limits.",
    "Added audit logging for reservation updates.",
    "Improved error messages and validation for booking conflicts.",
    "Developed a React dashboard with filters, calendar view, and alerts.",
    "Created a D3-based chart for weekly utilization."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js",
    "Caching",
    "Audit Logging",
    "Error Handling",
    "Testing"
  ]
}
---
stable-code:3b (invalid JSON)

---
codellama:7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app to help students log study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Added caching to reduce API latency and rate limits.",
    "Added audit logging for reservation updates.",
    "Improved error messages and validation for booking conflicts."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js"
  ]
}
---
tinyllama:1.1b (valid JSON)
{
   "project_name": "Campus Resource Trackers",
   "one_liner": "A web app to help students manage their study spaces, equipment loans, and lab availability.",
   "highlights": [
     "Logs study spaces, equipment loan requests, and lab availability in real-time for easy tracking and management."
   ],
   "skills": [
     "FastAPI endpoint for spaces, availability, and reservation management",
     "Cache live availability with TTL and retrieval using SQLAlchemy models",
     "React dashboard with filters, calendar view, and alerts"
   ]
}
---
smollm2:1.7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app to help students log study spaces, equipment loans, and lab availability.",
  "highlights": [
    "FastAPI endpoints for spaces, availability, and reservations.",
    "SQLAlchemy models for spaces, reservations, and users.",
    "D3-based chart for weekly utilization."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "D3.js"
  ]
}
---
falcon3:3b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web app to manage student study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Implemented caching mechanisms to enhance API performance and reduce rate limits.",
    "Added audit logging for reservation updates to ensure transparency and accountability.",
    "Improved error messages and validation for booking conflicts to provide better user experience."
  ],
  "skills": [
    "Web development",
    "API design",
    "Caching mechanisms",
    "Error handling",
    "Database modeling",
    "React UI development",
    "D3 visualization"
  ]
}
---
falcon3:7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web app to manage student resources, including study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Implemented caching to reduce API latency and handle rate limits.",
    "Added audit logging for reservation updates.",
    "Enhanced error messages and validation for booking conflicts."
  ],
  "skills": [
    "FastAPI for backend development",
    "React for frontend",
    "D3.js for data visualization",
    "SQLAlchemy for database modeling",
    "Caching mechanisms for performance optimization"
  ]
}
---
olmo2:7b (valid JSON)
{"project_name": "Campus Resource Tracker", "one_liner": "Developed a comprehensive web app to streamline campus resource management.", "highlights": ["Added caching to reduce API latency and rate limits", "Implemented audit logging for reservation updates", "Enhanced error messages and validation for booking conflicts"], "skills": ["FastAPI development", "React for UI", "SQLAlchemy ORM", "D3.js for data visualization", "Python testing frameworks"]}
---
openchat:7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app to help students log study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Implemented FastAPI endpoints for spaces, availability, and reservations.",
    "Developed SQLAlchemy models for spaces, reservations, and users.",
    "Created React dashboard with filters, calendar view, and alerts.",
    "Designed D3-based chart for weekly utilization."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3"
  ]
}
---
neural-chat:7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app to manage study spaces, equipment loans, and lab availability.",
  "highlights": [
    "FastAPI endpoints for spaces, availability, and reservations",
    "SQLAlchemy models for database management",
    "React dashboard with filters, calendar view, and alerts",
    "D3-based chart for weekly utilization",
    "Caching to reduce API latency and rate limits",
    "Audit logging for reservation updates",
    "Improved error messages and validation for booking conflicts"
  ],
  "skills": [
    "Python",
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js",
    "Testing frameworks (pytest, Jest)",
    "GitHub Actions"
  ]
}
---
starling-lm:7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Developed a web app to manage study spaces, equipment loans, and lab availability on campus.",
  "highlights": [
    "Implemented FastAPI endpoints for spaces, availability, and reservations.",
    "Created SQLAlchemy models for spaces, reservations, and users.",
    "Developed a React dashboard with filters, calendar view, and alerts.",
    "Integrated D3-based chart for weekly utilization analysis."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js"
  ]
}
---
dolphin-mistral:7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app to help students log study spaces, equipment loans, and lab availability.",
  "highlights": [
    "Developed FastAPI endpoints for spaces, availability, and reservations.",
    "Implemented caching to reduce API latency and rate limits.",
    "Added audit logging for reservation updates.",
    "Improved error messages and validation for booking conflicts."
  ],
  "skills": [
    "Python",
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js"
  ]
}
---
zephyr:7b (valid JSON)
{
  "project_name": "Campus Resource Tracker",
  "one_liner": "Web app to help students log study spaces, equipment loans, and lab availability.",
  "highlights": [
    "FastAPI endpoints for spaces, availability, and reservations.",
    "SQLAlchemy models for spaces, reservations, and users.",
    "React dashboard with filters, calendar view, and alerts.",
    "D3-based chart for weekly utilization.",
    "Caching to reduce API latency and rate limits.",
    "Audit logging for reservation updates."
  ],
  "skills": [
    "FastAPI",
    "SQLAlchemy",
    "React",
    "D3.js"
  ]
}
---

