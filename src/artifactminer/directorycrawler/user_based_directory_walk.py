

from datetime import datetime, timezone

from pytest import Session
from artifactminer.db.database import SessionLocal
from artifactminer.db.models import UserAnswer
from .directory_walk import user_keep_file, user_exclude_file, user_keep_extension, user_exclude_extension, is_extension, is_valid_filename
#from directory_walk import crawl_directory, userKeepFileName, user_exclude_file 
#here, I am assume am taking in ID 5 (File patterns to include/exclude)

#I'm asuming these constants are example of user input
INCLUDE_ANSWER_TEXT_EXAMPLE = ""
EXCLUDE_ANSWER_TEXT_EXAMPLE = "" 

IncludeKey = "file_patterns_include"
ExcludeKey = "file_patterns_exclude"

#db = SessionLocal() 


def get_user_data(db: Session): #retrieve data from DB   
    
    #stavan's requested python query but translated to SQL.
    sql = text("""
        SELECT ua.answer_text
        FROM user_answers AS ua
        JOIN questions AS q ON ua.question_id = q.id
        WHERE q.key = :question_key
        LIMIT 1
    """)
    
    include_result = db.execute(sql, {"question_key": IncludeKey}).fetchone()
    exclude_result =  db.execute(sql, {"question_key": ExcludeKey}).fetchone()
    print("Include:",include_result)
    print("Exclude:", exclude_result)

    include_arr = []
    exclude_arr = []

    if include_result is not None:
        include_arr = parse_user_input_text(str(include_result[0]))
    else:
        print("No include data found for user")

    if exclude_result is not None:
        exclude_arr = parse_user_input_text(str(exclude_result[0]))
    else:
        print("No exclude data found for user")

    for file in include_arr:
        if is_extension(file): #does the user input use *.<fileextension> or is it a filename? 
            user_keep_extension(file)
            continue
        if is_valid_filename(file) == False:
            print("filename", file, " is not a valid file") #TODO alert user? 
            continue
        else:
            user_keep_file(file)
    
    for file in exclude_arr:
        if is_extension(file): #does the user input use *.<fileextension> or is it a filename? 
            user_exclude_extension(file) 
        else:
            user_exclude_file(file)
    

#for testing purposes only.  
def add_user_answer(db, question_id: int, answer_text: str): #add data from DB
    ua = UserAnswer(question_id=question_id, answer_text=answer_text.strip())
    db.add(ua)
    db.commit()   
    db.refresh(ua)

def mock_adding_user_answer(): #TODO change this
    with SessionLocal() as db:
        #made some mock answers, but I'm assuming these are some on the expected answers given by the user.
        for includeAnswers in parse_user_input_text(INCLUDE_ANSWER_TEXT_EXAMPLE):
            add_user_answer(db, 5, includeAnswers)
        for excludeAnswers in parse_user_input_text(EXCLUDE_ANSWER_TEXT_EXAMPLE):
            add_user_answer(db, 6, excludeAnswers)

def delete_all_user_questions(db: Session): #for testing purposes only
    sql = text("DELETE FROM user_answers as ua WHERE ua.question_id = :question_key1 OR ua.question_id = :question_key2")
    db.execute(sql,{"question_key1": IncludeKey, "question_key2": ExcludeKey})
    db.commit()

def parse_user_input_text(text) -> list[text]: 
    #TODO add some more conditions for eronious input
    if text is None: 
        print("user input text is null.")
        return "text is null"
    else:
        return [x.strip() for x in text.split(",")]
    