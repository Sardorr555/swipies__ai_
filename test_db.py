import sys
import os
from peewee import MySQLDatabase, Model, CharField, BooleanField, DateTimeField, TextField

# Direct DB connection
DB = MySQLDatabase(
    'rag_flow',
    user='root',
    password='infini_rag_flow',
    host='127.0.0.1',
    port=5455
)

class User(Model):
    id = CharField(max_length=32, primary_key=True)
    email = CharField(max_length=255)
    nickname = CharField(max_length=100)
    referred_by_id = CharField(max_length=32, null=True)
    create_date = DateTimeField(null=True)

    class Meta:
        database = DB
        db_table = "user"

def main():
    print("Testing DB connection directly to MySQL...")
    try:
        DB.connect()
        print("Successfully connected to database!")
        
        # Check table columns first
        cursor = DB.execute_sql("DESCRIBE user;")
        columns = [row[0] for row in cursor.fetchall()]
        print(f"Columns in 'user' table: {columns}")
        
        if 'referred_by_id' not in columns:
            print("WARNING: referred_by_id is NOT in the database table columns!")
        else:
            print("referred_by_id column exists.")

        users = list(User.select())
        print(f"Total users in DB: {len(users)}")
        for u in users:
            print(f"User ID: {u.id}, Email: {u.email}, Nickname: {u.nickname}, Referred By: {u.referred_by_id}, Created: {u.create_date}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if not DB.is_closed():
            DB.close()

if __name__ == "__main__":
    main()
