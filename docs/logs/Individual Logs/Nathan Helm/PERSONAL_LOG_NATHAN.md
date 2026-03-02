<!--
TO TA: As requested, from now on all weekly logs will be added in this file here.
-->

<h1>PERSONAL LOG-- 25/01/2026</h1>

<h3> Schedule</h3>

- Monday: checkin

- Wednsday: no class, alternating week

- Thursday: Spoke in discord team meeting, talked to Shlok, Stavan, and Evan. Talked about CLI and weekly tasks. Evan and I were responsible for the CLI tool for peer testing.

- Friday: Evan and I booked a room. We began working the CLI tool. Most of the development was done but I suggested adding API async functions to the CLI tool for data accuracy, code reusability among other things.


**Duties & Hyperlinks**

This week I was responsible for multiple tasks...

# Coding Tasks

The first task I worked on was resolving issue 302, which state to replace local CLI function with API async functions as I state to my team, 
"I noticed that the CLI currently retrieves and sends data using direct database calls and local functions. While this works, I’m planning to replace some of this logic with our API calls (which provide similar functionality) so that data handling remains consistent across the system. The API may process data differently than local logic—such as invoking additional functions or validations—and using it helps prevent potential data inconsistencies." 

The function improvments were: 

- zip upload
- user_info (getting email)
- consent
- get_AI_summaries (NEW)

the CLI output works as expected.

here is the PR that resolved the issue: https://github.com/COSC-499-W2025/capstone-project-team-1/pull/306


# Testing Tasks

This is the tests I made for my API requests and the CLI changes: 

### in test_retrieval

- test_AI_summaries_other_user()
- test_AI_summaries_filters_by_email_and_repo()

### in test_cli.py:

run 'uv run api' to a tables.
test all functions this is a refactoring more than it is a new feature


https://github.com/COSC-499-W2025/capstone-project-team-1/pull/282/files#diff-168f034869cc1d3ab293249cc2d88be4254543a679e0e89908d42490384df683

# Reviewing Tasks
I also made critical pr reviews on these two PRs. 

- https://github.com/COSC-499-W2025/capstone-project-team-1/pull/301

- https://github.com/COSC-499-W2025/capstone-project-team-1/pull/299


**Reflection & Team Dynamic**

I’m really proud of our team and how effectively we collaborate. I appreciate how responsive we are with our pull requests, which keeps our workflow smooth and efficient. I’m also excited about my current task and feel confident in my understanding of my responsibilities at this stage.

**Next Week** 

This upcoming week, I will work on milestone #2 and help develop our frontend TUI.  

![weekly](/docs/logs/Individual%20Logs/Nathan%20Helm/Image/Jan25.png)

<hr>

<h1>PERSONAL LOG-- 08/02/2026</h1>

<h3> Schedule</h3>

- w1 Monday: checkin

- w1 Wednsday: no class, alternating week

- w1 Thursday: meeting, discussing tasks

- w2 Monday: checkin

- w2 Wednsday: no class, alternating week

- w2 Friday: spoke with Evan to discuss our tasks. I was leading file intelligence. 

**Duties & Hyperlinks**

Over these past 2 weeks I worked on few things. The first thing was implementing issue 346,
which was implementing the crawler system to the file intelligence. Once I had finished that, I was tasked with adding an api endpoint to the crawler system and file intelligence system. 

# Coding Tasks

The function improvements were: 

- get_file_intelligence_contents
- get_crawler_pdf_contents

API endpoints:




here is the PR that resolved the issue: https://github.com/COSC-499-W2025/capstone-project-team-1/issues/346


# Testing Tasks

This is the tests I made for my API requests and the CLI changes: 

- test_ignore_files
- append_file_to_path
- test_api_call

![weekly](/docs/logs/Individual%20Logs/Nathan%20Helm/Image/s1.png)

![weekly](/docs/logs/Individual%20Logs/Nathan%20Helm/Image/s2.png)

# Reviewing Tasks
I also made a strong PR review. Where I went in depth and provided screenshots

-https://github.com/COSC-499-W2025/capstone-project-team-1/pull/362


**Reflection & Team Dynamic**

I’m proud of the way our team collaborates and supports one another. Our responsiveness with pull requests makes a big difference in keeping our workflow efficient. I’m also excited about the work I’m currently doing and feel confident in my understanding of what’s expected of me.

**Next Week** 

This upcoming week, I add more to file intelligence and provide another extension.

![weekly](/docs/logs/Individual%20Logs/Nathan%20Helm/Image/Feb8.png)