

from datetime import datetime, timezone

from sqlalchemy import text
from artifactminer.db.database import SessionLocal
from artifactminer.db.models import UserAnswer
from .directory_walk import user_keep_file, user_exclude_file
#from directory_walk import crawl_directory, userKeepFileName, user_exclude_file 
#here, I am assume am taking in ID 5 (File patterns to include/exclude)

#I'm asuming these constants are example of user input
INCLUDE_ANSWER_TEXT_EXAMPLE = ""
EXCLUDE_ANSWER_TEXT_EXAMPLE = "" 


db = SessionLocal() 


def get_user_data(): #retrieve data from DB   
    query1 = text("SELECT answer_text FROM user_answers WHERE question_id = 5;")
    query2 = text("SELECT answer_text FROM user_answers WHERE question_id = 6;")
    include_result = db.execute(query1)
    exclude_result = db.execute(query2)
    include = [row[0] for row in include_result.fetchall()]
    exclude = [row[0] for row in exclude_result.fetchall()]
    print("Include:", include)
    print("Exclude:", exclude) 
    for t in include:
        user_keep_file(t)
    for t in exclude:
        user_exclude_file(t)

        
def add_user_answer(db, question_id: int, answer_text: str): #add data from DB
    new_answer = UserAnswer(
        question_id=question_id,
        answer_text=answer_text,
        answered_at=datetime.now(timezone.utc)
    )
    db.add(new_answer)
    db.commit()
    db.refresh(new_answer)
    return new_answer

def mock_adding_user_answer(): #TODO change this
    with SessionLocal() as db:
        #made some mock answers, but I'm assuming these are some on the expected answers given by the user.
        for includeAnswers in parse_user_input_text(INCLUDE_ANSWER_TEXT_EXAMPLE):
            add_user_answer(db, 5, includeAnswers)
        for excludeAnswers in parse_user_input_text(EXCLUDE_ANSWER_TEXT_EXAMPLE):
            add_user_answer(db, 6, excludeAnswers)

def delete_all_users(): #for testing purposes only
    db.execute(text("DELETE FROM user_answers WHERE question_id = 5 or question_id = 6;"))
    db.commit()

def parse_user_input_text(text) -> list[text]: 
    #TODO add some more conditions for erronious input
    if text is None: 
        print("user input text is null.")
        return "text is null"
    else:
        return [x.strip() for x in text.split(",")]
    

'''
mock_adding_user_answer()
get_user_data()
delete_all_users() #run last
'''