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



<hr>

<h1>PERSONAL LOG-- 01/03/2026</h1>

![weekly](/docs/logs/Individual%20Logs/Nathan%20Helm/Image/Mar1.png)

<h3> Schedule</h3>

- Monday: Presentations

- Wednsday: no class, presentations

- Saturday: meeting, discussing tasks



# Coding Tasks

Pull Requests:

- https://github.com/COSC-499-W2025/capstone-project-team-1/pull/392 

- https://github.com/COSC-499-W2025/capstone-project-team-1/pull/411


 


# Testing Tasks

These are the tests I made for my PRs: 
### PR 1 ###
- test_user_based_directory_walk()
- test_exclude_file_user_setting()
- test_include_file_user_setting()
- test_gathered_files_from_oswalk()

### PR 2 ###
- test_custom_ranking_rank_must_be_ge_1()
- test_invalid_comparison_attribute_raises()
- test_accepts_valid_payload_and_parses_dates()
- test_defaults_are_empty_lists()




# Reviews

Here are my pr reviews:

- https://github.com/COSC-499-W2025/capstone-project-team-1/pull/393

- https://github.com/COSC-499-W2025/capstone-project-team-1/pull/406




**Reflection & Team Dynamic**

I really value the strong sense of teamwork we have and the way everyone shows up for each other. Our feedback on pull requests helps keep things moving smoothly and prevents bottlenecks. I’m also feeling energized by the projects on my plate right now and have a solid grasp of my responsibilities and goals.

**Next Week** 

This upcoming week, I will work on our frontend and prepare for PR testing. 

--

<hr>

<h1>PERSONAL LOG-- 08/03/2026</h1>

![weekly](/docs/logs/Individual%20Logs/Nathan%20Helm/Image/Mar8.png)

<h3> Schedule</h3>

- Monday: No class

- Wednsday: Quiz 3

- Saturday: disscuss tasks on discord



# Coding Tasks

Pull Requests:

- https://github.com/COSC-499-W2025/capstone-project-team-1/pull/460


- https://github.com/COSC-499-W2025/capstone-project-team-1/pull/449

 


# Testing Tasks

These are the tests I made for my PRs: 

### pr 2 handled all tests for pr 1 
> test_valid_zip_path
test_rejects_empty_zip_path
test_requires_zip_path
test_valid_candidate
test_all_fields_required
test_serialization
test_with_multiple_repos
test_empty_repos
test_deserialization
test_valid_repo_ids
test_single_repo_id
test_rejects_empty_list
test_complete_identity
test_optional_name
test_zero_counts
test_minimal_request
test_with_intake_id
test_custom_models
test_rejects_empty_repo_ids
test_rejects_short_email
test_rejects_empty_model
test_valid_response
test_all_valid_statuses
test_rejects_invalid_status
test_defaults
test_with_progress
test_all_stages
test_rejects_invalid_stage
test_queued_status
test_with_draft
test_with_output
test_with_error
test_with_messages
test_defaults
test_with_feedback
test_success
test_all_statuses
test_cancelled
test_failed_cancel
test_full_generation_flow
test_cancellation_flow



# Reviews

Here are my pr reviews:

- https://github.com/COSC-499-W2025/capstone-project-team-1/pull/461

- closed but worth mentioning: 
https://github.com/COSC-499-W2025/capstone-project-team-1/pull/448



**Reflection & Team Dynamic**

I truly appreciate the strong sense of teamwork we share and how everyone supports one another. The feedback we provide on pull requests helps maintain smooth progress and avoids any bottlenecks. I’m also feeling motivated by my current projects and have a clear understanding of my responsibilities and objectives.

**Next Week** 

This upcoming week, I will work migrating more code to handle milestone 3.


