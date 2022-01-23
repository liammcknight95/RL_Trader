import sqlite3
from datetime import datetime


def get_all_db_tables(db=':memory:'):

    conn = sqlite3.connect(db) # can pass a file 'filename.db' or make an in memory db - ':memory:' # './local_data/text_data.db'
    c = conn.cursor() # create a cursor
    c. execute("SELECT name FROM sqlite_master WHERE type='table';")
    print(c.fetchall())
    conn.close()


def create_psaw_table(db=':memory:'):

    conn = sqlite3.connect(db) # can pass a file 'filename.db' or make an in memory db - ':memory:' # './local_data/text_data.db'
    c = conn.cursor() # create a cursor


    c.execute('''
        CREATE TABLE IF NOT EXISTS reddit_psaw_submissions (
            psaw_id text NOT NULL,
            psaw_author text,
            psaw_created_utc text,
            psaw_subreddit text,
            psaw_title text,
            psaw_selftext text,
            psaw_full_link text,
            PRIMARY KEY (psaw_id)
        )
    ''')
    conn.commit()

    conn.close()


def create_praw_tables(db=':memory:'):

    conn = sqlite3.connect(db) # can pass a file 'filename.db' or make an in memory db - ':memory:' # './local_data/text_data.db'
    c = conn.cursor() # create a cursor

    # create main praw table
    c.execute('''
        CREATE TABLE IF NOT EXISTS reddit_praw_submissions (
            praw_fullname text NOT NULL,
            praw_id text NOT NULL,
            praw_author text,

            -- redundant from psaw, keept for now for testing
            praw_created_utc text,
            praw_subreddit text,
            praw_subreddit_id text,
            praw_title text,
            praw_selftext text,
            praw_permalink text,
            praw_url text,

            -- some post quality metrics
            praw_num_comments integer,
            praw_score integer,
            praw_ups integer,
            praw_upvote_ratio real,
            praw_comment_ids blob,
            PRIMARY KEY (praw_fullname)
        )
    ''')

    # create praw comments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS reddit_praw_comments(
            praw_comment_fullname text NOT NULL,

            -- comment unique identifier
            praw_comment_id text NOT NULL,

            -- parent comment id
            praw_comment_parent_id text NOT NULL,

            -- main submission id
            praw_comment_link_id text,
            
            -- comment related data
            praw_created_utc text,            
            praw_comment_body text,
            praw_comment_score integer,

            PRIMARY KEY (praw_comment_fullname)
        )
    ''')

    conn.commit()

    conn.close()


def insert_new_psaw_submission(submission, db=':memory:'):
    
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
            INSERT INTO reddit_psaw_submissions VALUES (
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


def insert_new_praw_submission(praw_submission_values, db=':memory:'):
    
    conn = sqlite3.connect(db)
    c = conn.cursor()
    # using conn as a context manager to avoid explicitly committing every time
    with conn:

        
        # praw_submission_values = {
        #     'praw_fullname':submission.fullname,
        #     'praw_id':submission.id,
        #     # 'author':submission.author,
        #     'praw_created_utc':datetime.fromtimestamp(int(submission.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
        #     'praw_subreddit':submission.subreddit.display_name,
        #     'praw_title':submission.title,
        #     'praw_selftext':submission.selftext,
        #     'praw_full_link':submission.url,

        #     'praw_num_comments':submission.num_comments,
        #     'praw_score':submission.score,
        #     'praw_upvote_ratio':submission.upvote_ratio
        # }

        c.execute(f'''
            INSERT INTO reddit_praw_submissions VALUES (
                :praw_fullname,
                :praw_id,
                :praw_author,
                :praw_created_utc,
                :praw_subreddit,
                :praw_subreddit_id,
                :praw_title,
                :praw_selftext,
                :praw_permalink,
                :praw_url,
                :praw_num_comments,
                :praw_score,
                :praw_ups,
                :praw_upvote_ratio,
                :praw_comment_ids
            )
        ''', praw_submission_values)

    conn.close()


def insert_new_praw_comment(comment, db=':memory:'):
    
    conn = sqlite3.connect(db)
    c = conn.cursor()
    # using conn as a context manager to avoid explicitly committing every time
    with conn:

        praw_comments_values = {
            'praw_comment_fullname':comment.fullname,
            'praw_comment_id':comment.id,
            'praw_comment_parent_id':comment.parent_id,
            'praw_comment_link_id':comment.link_id,
            'praw_comment_created_utc':datetime.fromtimestamp(int(comment.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
            'praw_comment_body':comment.body,
            'praw_comment_score':comment.score
        }


        c.execute(f'''
            INSERT INTO reddit_praw_comments VALUES (
                :praw_comment_fullname,
                :praw_comment_id,
                :praw_comment_parent_id,
                :praw_comment_link_id,
                :praw_comment_created_utc,
                :praw_comment_body,
                :praw_comment_score
            )
        ''', praw_comments_values)

    conn.close()


def get_reddits(table, db=':memory:'):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute(f"SELECT * FROM {table}")#, {'ups':ups_threshold})
    results =  c.fetchall()
    conn.close()

    return results