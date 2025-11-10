
# logs - week-8 

* Got to know in mondays class that some merge conlicts were inadvertently introduced into development branch. Fixed the issue in the class itself and opened up a PR for the same. 

* Noticed that user config questions we getting inserted into the database instead of upserting. Fixed the same and also added comma seperated include and exlude file extensions to the user config questions. Opened up a PR for the same as well as documented how to use it to Nathan as it handles the next logic. 

* Reviewed a bunch of PR's including the repo analysis done by Evan, TUI changes by Ahmad, OPENAI endpoint by Shlok, added appropriate comments on Nathans PR so that he knows how to extract user config questions form db. 

* Added zip endpoints to API as well as tests so TUI doesnt need to mock. Currently directories are getting mocked but from API layer. Once Brendans PR is merged, I will integrate the same to API and hence TUI. 


| **task**                    | **status**     | **notes**      |
| --------------------------- | -------------- | -------------- |
| start integrated api with frontend and backend with shared models | ■■ Done | |
| Add alembic migrations to db, so teammates dont have to delete db while testing PR's| ■■ Not started yet. | Will pick this pick up this week.  |
|Look into having github actions setup which runs pytest automatically on opened PR's| ■■ Not started yet. | Did not start this yet as some tests still depend on hardcoded values. |
|Help evan in repo analysis as we get closer to milestone 1. | ■■ Not started yet. | Planned for reading break. |


