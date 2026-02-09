Term 2 Week 1: [Week 15 (Jan 5 - Jan 11)](Week_15.md) 
Term 2 Week 2: [Week 16 (Jan 12 - Jan 18)](Week_16.md)

---
## Term 2 Week 4-5: Jan 26- Feb 8

**My Code Contributions For Week 4**
I worked on [Issue 321](https://github.com/COSC-499-W2025/capstone-project-team-1/issues/321) which was about being able to actually view the user's file system instead of the mock data that was shown. The [PR](https://github.com/COSC-499-W2025/capstone-project-team-1/pull/347) for that issue created 2 utilities: a file crawler using `fdir` and then fuzzy searching over that crawled list of files using `fuse.js`.

Note: we are finally switching to OpenTUI which is so much better than Textual and glad that development on the TUI has started

**My Code Contributions for Week 5**:
1. Worked on [Issue 330](https://github.com/COSC-499-W2025/capstone-project-team-1/issues/330) which creates the `GET /resume/{id}` endpoint as required by Milestone 2. The PR for the new endpoint be found [here](https://github.com/COSC-499-W2025/capstone-project-team-1/pull/351). 

2. Worked on [Issue 339](https://github.com/COSC-499-W2025/capstone-project-team-1/issues/339) which incorporates allows the user to add evidences of their sucess in a particular project such as metrics and awards which is again a requirement for Milestone 2. Created a new `ProjectEvidence` model. The PR for this issue is [here](https://github.com/COSC-499-W2025/capstone-project-team-1/pull/352).

3. I made progress on incorporating a local LLM as a part of our analysis using a prebuilt llama.cpp server binary which exposes OpenAI compatible endpoints which simplifies API calls to the local LLM. This is NOT a code contribution but rather surfacing my research over the past week and showing it to the team. Everyone is excited to use it and we are planning on improving our analysis pipeline to use the local LLM efficiently. The PR can be found [here](https://github.com/COSC-499-W2025/capstone-project-team-1/pull/360)

**Reviewing Team's PRs- Week 4**:
1. Reviewed [Evan's PR](https://github.com/COSC-499-W2025/capstone-project-team-1/pull/317) on a file path issue. Requested changes which were promptly fixed by him
2. Reviewd [Stavan's PR](https://github.com/COSC-499-W2025/capstone-project-team-1/pull/342) as he added a `GET /projects` endpoint. Requested changes which were promptly fixed.
3. Reviewed [Stavan's PR](https://github.com/COSC-499-W2025/capstone-project-team-1/pull/343) as he added a `GET /projects/{id}` endpoint. No changes were required.
4. Reviewed [Ahmad's PR](https://github.com/COSC-499-W2025/capstone-project-team-1/pull/344) as he added an API client layer for the TUI. Requested some changes which were promptly addressed.
5. Reviewed [Ahmad's PR](https://github.com/COSC-499-W2025/capstone-project-team-1/pull/344) as he added a global state layer for the TUI. I didnt have much to say as Stavan had already requested changes which Ahmad had applied.


**Reviewing Team's PR- Week 5**:
1. Reviewed [Stavan's PR](https://github.com/COSC-499-W2025/capstone-project-team-1/pull/350) as he added a new `GET /skills` endpoint. I requested some changes that Stavan addressed.
2. Reviewed [Stavan's PR](https://github.com/COSC-499-W2025/capstone-project-team-1/pull/357). Nothing to note.
3. Reviewd [Ahmad's PR](https://github.com/COSC-499-W2025/capstone-project-team-1/pull/361) as he added some test cases and a `mock_projects_v2.zip` file for everyone to have a user simulated zip file to test their work.
4. Reviewed [Evan's PR](https://github.com/COSC-499-W2025/capstone-project-team-1/pull/362) as he added a `POST /resume/generate` endpoint. Requested some changes which Evan fixed in the PR. 


**Plan for Next Week**:
We wish to complete all Milestone 2 objectives soon. I plan to work with Evan on the local LLM side to figure out the context that we give to the LLM.

![T2Week5](T2Week5.png)

## Term 2 Week 3: Jan 19- Jan 25:

## Term 2 Week 3: Jan 19- 25:

#### Previous Week:
The previous week was focused on creating a test bench to experiment with adding local LLMs through Ollama.


#### Brief:

**Task 1**
Picking up from last week I created an internal tool (not a part of the repo) to see if I can serve a local LLM (LiquidAI's LFM2.5-1.2B-Instruct) research on the feasibility of this feature. Turns out, it is notoriously difficult to actually generated a reliable JSON Schema from small LLMs. It is looking increasingly unlikely that I can serve a local LLM for on-device analysis of the user's zip file

**Task 2**
Next order of business was to look at possible options at revamping the TUI that we have from Textual to OpenTUI. Every group that is creating a TUI like us is likely to use Textual and thus we risk our project to not be visually appealing. Thankfully, OpenTUI solves that. It is a much better library of TUI components and animations which can be coded through React. So my focus was on researching on what OpenTUI is and how do we use it and is it even feasible to migrate to it. PR #297: Experimented with OpenTUI and have a mock ready is my work on OpenTUI for the team to have a look and provide feedback. 

https://github.com/COSC-499-W2025/capstone-project-team-1/pull/297

**Task 3**
As a part of my maintenance of the codebase, I found that we were using a deprecated datetime utility that was causing issues across the API.  Rather than just patching the email bug, I took the opportunity to refactor the entire codebase's datetime handling. The fix involved removing the deprecated `utcnow()` helper function and standardizing all datetime assignments to use `datetime.now(UTC).replace(tzinfo=None)` directly. Look at PR: #304: API Cleanup: Fix Broken Timestamp Assignment and Standardize Naive UTC Datetimes

https://github.com/COSC-499-W2025/capstone-project-team-1/pull/304

**Task 4**
There was a race condition for the PR: 295 Implement Intiailization on OpenAI wherein 2 requests could create the same OpenAI client, there was no thread lock in place which I flagged and helped work on the fix with Evan

https://github.com/COSC-499-W2025/capstone-project-team-1/pull/295



#### Plan for Next Week
The team will be implementing any and all feedback that is given to us in the Peer Testing. Ill be researching more into OpenTUI and will be working with the team to prioritize tasks. We might put OpenTUI on the backfoot and prioritize Milestone 2.

I need to work more on the code maintenance and looking at the APIs in detail as I believe that there is a lot of scope for optimization and refactoring. 


![T2Week3 Sprint Tasks](T2Week3.png)