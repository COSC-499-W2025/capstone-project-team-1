

from datetime import datetime
from artifactminer.db.database import SessionLocal
from artifactminer.db.models import UserAnswer
import pprint
#from directory_walk import crawl_directory, userKeepFileName, user_exclude_file 
#here, I am assume am taking in ID 5 (File patterns to include/exclude)

INCLUDE_ANSWER_TEXT_EXAMPLE = ["mock2.js", "bugbomb.log"] 
EXCLUDE_ANSWER_TEXT_EXAMPLE = ["mock2.js", "bugbomb.log"] 
db = SessionLocal() 

def get_user_data():
        
        include = db.query(UserAnswer).filter(UserAnswer.question_id == 5).first()
        exclude = db.query(UserAnswer).filter(UserAnswer.question_id == 6).first()
        pprint.pprint(include) #here I am assuming we require 
        pprint.pprint(exclude)
        
def add_user_answer(db: Session, question_id: int, answer_text: str):
    new_answer = UserAnswer(
        question_id=question_id,
        answer_text=answer_text,
        answered_at=datetime.now(datetime.timezone.utc)
    )
    db.add(new_answer)
    db.commit()
    db.refresh(new_answer)
    return new_answer

def mock_adding_user_answer():
    #made some mock answers, but I'm assuming these are some on the expected answers given by the user.
    add_user_answer(db, 5, INCLUDE_ANSWER_TEXT_EXAMPLE)
    add_user_answer(db, 6, EXCLUDE_ANSWER_TEXT_EXAMPLE)

mock_adding_user_answer()
get_user_data()