
def test_database_connection():

	from sqlalchemy import text
	from artifactminer.db.database import engine

	with engine.connect() as conn:# Basic connection test 
		result = conn.execute(text("SELECT 1")).scalar()
		assert int(result) == 1