# Evan Crowley
## Log: January 11 2026


### From Peer Review
![Tasks_I_Did](Tasks%20Jan5-11.png)


### Monday
Got together as a team and determined what we wanted to get started on this semester. Got a rough plan down for when we wanted to meet next.


### Friday
Got together over discord and made a plan for what we wanted to have done by Sunday.


### Saturday
Worked on integrating Ollama into the AI processing method. Basically having Ollama as an option to replace ChatGPT requires no API key.


### Worked on this week:
- Added the ability to use Ollama instead of chatGPT
- Changed necessary methods so that Ollama can be chosen if that is the users selected AI model
- Created tests for Ollama AI analysis, similar to the chatGPT analysis


### Reflection:
This week I was able to add basic Ollama integration. Having the ability to choose between a fully local model and one online I think will not only add security but allow the program to be used by those who do not have an API key for chatGPT.


### Team Dynamic:
We determined what needed to be done on Friday. Overall I think that those who were given a task were able to complete it in a timely manner.


### Plan
For next week I want to work on the AI analysis more and determine what model will be best to be run locally through Ollama. I would also like to work on the output and see what can be done for outputting helpful user information.



# Evan Crowley
## Log: January 18 2026




### From Peer Review
![Tasks_I_Did](Tasks%20Jan12-18.png)




### Monday
Got together and worked on a schedule for the week. We decided to get together on Saturday to discuss future work before the next milestone.


### Saturday
We had a group meeting where we decided on what should be done before the milestone. Split up work evenly among the group members that could make it. I worked on getting async openAI calls working.


### Sunday
Managed to get the async calls working and created some tests. Made a log for this week.


### Worked on this week:
- Added the ability to use OpenAI asynchronously. This allows the user to make multiple calls at once, and not having to wait for the last completed call
- Added tests to show the efficiency of synchronous vs asynchronous calls.




### Reflection:
This week I was able to add Asynchronous calling for openAI. It was fairly easy to add and it generally should speed up the calls, as more can be done at once.


### Team Dynamic:
This week was good, most people in the team were there for the meeting, adn everyone was able to help each other when needed.
### Plan
For next week I want to work on further file analysis. I want to deepen the analysis of files not included in repositories and make sure that there is working AI and non-AI analysis for the peer review and milestone.




# Evan Crowley
## Log: January 25 2026




### From Peer Review
![Tasks_I_Did](Tasks%20Jan19-25.png)




### Monday
Got together as a group and determined we needed to get the APIs solved and a CLI together. Nathan and I decided to work on the CLI together.

### Thursday
Got together with Natahan and created a non-interactive CLI. 


### Sunday
Determined what we wanted to mention during the peer review.


### Worked on this week:
- non-interactive CLI was created
- made tests for the non-interactive CLI


### Reflection:
Got the CLI working this week. It was determined that that should take top priority in order to be ready for the peer review.


### Team Dynamic:
Good, we worked together this week to make sure everyone was ready for the peer review.

### Plan:
Continue to work on file analysis outside of repositories. I want to make sure that full file analysis is ready before the next milestone.













# Evan Crowley
## Log: February 8 2026








### From Peer Review
![Tasks_I_Did](Screenshot%202026-02-08%20190529.png)








Week 1 = Monday Jan 26th
### Tuesday
I fixed an issue with the file path variations in the CLI. I added some code so that when the user gives slight variations of the file path it still works correctly.


Started work on the file analysis system. Created the initial file intelligence main python file with pdf analysis. Created a unit test for testing pdf analysis.


### Wednesday
Refined PDF analysis to be able to detect if a PDF is a resume


### Worked on this week:
- CLI bug fixes
- Starting PDF file analysis


Week 2 = Monday February 2nd
### Saturday
Worked on milestone issue #331 add generate resume endpoint. Created the endpoint for on demand resume generation, using a combination of previously made functions, as well creating the new resume generation function. Added the ability for the user to "regenerate" their resume by deleting the old one on generation of the new one. Created testing to ensure full file functionality.


### Reflection:
Got bug fixes and new features put in for both weeks. Overall I think I managed to get some good additions into the project, and some bug fixes as well. The tests I added should help with any future debugging and there are improvements to be made to the resume generation endpoint when some of the soft dependencies are added.




### Team Dynamic:
Overall this week we worked well as a team and managed to support each other when needed. Nathan and I collaborated on getting the file analysis started. He picked it up after I added the pdf analysis, and integrated his file analysis code into the process.


### Plan:
I plan to continue working on file analysis but primarily want to focus on local AI and open AI prompt engineering. I want to find the most efficient prompt to get the correct information from both our local and cloud based LLMs. I plan on discussing my findings with Shlok at some point through the week.








# Evan Crowley
## Log: March 1 2026



### From Peer Review
![Tasks_I_Did](Tasks%20March1.png)


### Week 4 Feb 16 - 22
Began work on issue number 333 branch “333-Add-GET-/portfolio/{id}-endpoint” in order to get ready for the milestone presentation. Removing the legacy POST /resume/generate endpoint and its schemas.


### Week 5 Feb 23 - March 1
Had our milestone #2 presentations. We presented last and managed to get out the majority of what we wanted to mention. Addressed issues in the “333-Add-GET-/portfolio/{id}-endpoint” PR. Ensured there were no merge conflicts. Worked on issue 396, submitted for PR review and it was determined that it would be addressed in a different branch. Determined what we needed to get done before the end of the term, and what to expect on the quiz this Wednesday.


### Reflection:
This week was good, I was able to finalize some tasks and complete the presentation. I think that overall there was some good additions and that next week should see some good progress.


### Team Dynamic:
Good, we worked together this week to make sure everyone was ready for the peer review.


### Plan:
Address all the branch migrations we have to do before the end of the semester in order to have the “experimental-llamacpp-v3” fully integrated into the development branch.

# Two Week log from Feb 23 to March 8
# Week 1 Feb 23 - March 1
Evan Crowley
Log: 


### From Peer Review
![Tasks_I_Did](Tasks%20March2-8.png)

### Week summary:
This week I got a couple PRs done that I had been working on over the week. I had a PR that was determined would be done in parallel with someone else's work.

#### My Prs:
#393 - Issue 333 add get /portfolio/{id} endpoint
#405 (Closed not merged)- Issue 396-Refactor-skills-models-into-deep_analysis-module

#### My Pr Reviews:
#410 - dedupe PortfolioEditRequest via inheritance, clean up tests

# Week 2 March 2 - 8
### Monday
We had no class due to the guest lecture.

### Wednesday 
Had the third quiz, overall I think it went alright. I wish there was more time, and I had a more solid grasp of what to study for, but overall I did the best I could.

### Saturday
Worked most of the day on issue #397 (Ollama to llama.cpp migration). It was determined as a group what else we wanted to get done before the next peer review so my work was shelved and given to Shlok for further development. I ended up getting pretty far in that issue, but I think that Shlok is more familiar with that migration so it's for the best.
Sunday
Worked on issue #438 (Local LLM API Endpoints). Created /local-llm/context intake endpoint with a zip repository discovery. Wrote some tests for the local LLM API, and made sure it had proper error handling.

### My Prs:
#461 - Issue 438 local intake endpoint and register router

#448 (Closed not merged) - Issue 397 replace ollama with local llm wrapper and update consent levels

### My Pr Reviews:
#449 - Issue 437 transport schemas

#436 - feat(opentui): add pipeline API types and screen updates


### Reflection:
This week I was able to get a lot done, and I'm satisfied with the work this week. I think that given what we talked about we should be on track for next week's peer reviews, so I'm going to be working on that.


### Team Dynamic: 
Overall I think we did good this week, and expect a similar effort from the group next week.

### Plan:
I plan to continue working on the github issues so that our project is reviewed for peer reviews next week. I am going to be working on #440 for next week.





### Week March 9 - 15
Evan Crowley


### From Peer Review
![Tasks_I_Did](Tasks%20March9-15.png)

### Monday
We got together as a group and discussed what we did the week before. We determined what we needed to get done over the coming week, and what we needed to have before peer reviews.

### Saturday
Connected with Nathan about what we need to do in order to continue working on issues. Determined that the issue I need would be done by next day which is when I could start work on that issue

### Sunday
Completed a PR closing issue #440. Reviewed #479 in order to complete an issue thats a dependency for issue #440 .

### My Prs:
#482 - Issue 440 generation start endpoint

### My Pr Reviews:
#479 - Issue #439, Contributor Discovery Endpoint added.

#478 - OpenTUI Migration PR7b: FeedbackScreen


### Reflection:
This week was good, I had a few other classes that I had to work on so I didn't get as much done as I wanted, but I still managed to work on a PR and review a couple PRs. I also worked on the peer testing task list for this week.
Team Dynamic:
We worked good as a team this week and communicated about who needed to get what done. We ended up being able to get a lot done this week and I think the peer review tomorrow will go well.

### Plan:
My plan is to continue the work of transferring work from the experimental branch into development. I hope to get at least two or three issues done next week so that we're ready for the final milestone deadline.



