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







