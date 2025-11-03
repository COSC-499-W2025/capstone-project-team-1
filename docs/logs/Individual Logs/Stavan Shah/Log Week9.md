# logs - week-8 

* This week, under the user configuration questions, I added a question to ask the user about their email address, this will help the repo analysis tool to identify our user in collaborative git repos. 

* I also saved all the user configuration answers from the TUI into our DB, which stores answer in user_answers table.

* While I opened up the PR for the above 2 changes, I was made aware a flaw which made editing,deleting and adding new user configurations very difficult. I was using the database ids to map each question. Which I dropped and started using "keys" for each questions. This will let us do CRUD on user configurations way easier. 

* Opened up the PR for that issue. 

* Reviewed Ahmad's PR which solved bugs into our TUI , Shlok's PR which added file browsing option to the TUI and Evan's PR which added git repo analysis to our codebase. 



| **task**                    | **status**     | **notes**      |
| --------------------------- | -------------- | -------------- |
| start integrated api with frontend and backend with shared models | ■■ in progress |  Was halted this week due to point 3 bug. |
| coded a questions endpoint to fetch user questions from db | ■■ done | optional notes |
| integrated the new questions endpoint to the frontend and display question on tui| ■■ done | optional notes | 
| store user answers to those questions in the database in new table | ■■ Completed | optional notes |
| Add alembic migrations to db, so teammates dont have to delete db while testing PR's| ■■ Not started yet. | optional notes |
|Look into having github actions setup which runs pytest automatically on opened PR's| ■■ Not started yet. | optional notes |


