import sqlite3
from datetime import datetime

def create_subreddit_table(db=':memory:'):

    conn = sqlite3.connect(db) # can pass a file 'filename.db' or make an in memory db - ':memory:' # './local_data/text_data.db'
    c = conn.cursor() # create a cursor


    c.execute('''
        CREATE TABLE IF NOT EXISTS reddit_test (
            id text,
            author text,
            created_utc text,
            subreddit text,
            title text,
            selftext text,
            full_link text,
            PRIMARY KEY (id)
        )
    ''')
    conn.commit()

    # # TODO use execute many instead for bulk upload
    # [insert_new_reddit(entry) for entry in final_df.to_dict('records')]

    # reddits = get_reddits(0)
    # columns = [d[0] for d in c.description]

    conn.close()


def insert_new_reddit(submission, db=':memory:'):
    
    conn = sqlite3.connect(db)
    c = conn.cursor()
    # using conn as a context manager to avoid explicitly committing every time
    with conn:
        values = {
            'id':submission.id,
            'author':submission.author,
            'created_utc':datetime.fromtimestamp(int(submission.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),#str(submission['created_utc']),
            'subreddit':submission.subreddit,
            'title':submission.title,
            'selftext':submission.selftext,
            'full_link':submission.full_link
        }

        c.execute(f'''
            INSERT INTO reddit_test VALUES (
                :id,
                :author,
                :created_utc,
                :subreddit,
                :title,
                :selftext,
                :full_link
            )
        ''', values)

    conn.close()


def get_reddits(db=':memory:'):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("SELECT * FROM reddit_test")#, {'ups':ups_threshold})
    results =  c.fetchall()
    conn.close()

    return results