import os, sys
sys.path.append(os.getcwd())

import pandas as pd
from datetime import datetime
import AlternativeData.reddit_sql as reddit_sql
from timer import Timer
import logging

# loop, time and put in a py file and keep running
@Timer(text="# Total time elapsed: {:.2f} seconds", logger=logging.info)
def fetch_submissions(api, start_datetime, end_datetime, freq, subreddits, db_path, logger=None):
    ''' 
    Function that fetches submissions between a start and datetime for a group of subreddits
        api: PushShift api object
        start_datetime: stingtime in the format: '%Y-%m-%d'
        end_datetime: stingtime in the format: '%Y-%m-%d'
        freq: string, ie '1D', '6H' etc
        subreddits: list ie ['bitcoin','wallstreetbets','cryptocurrency']
        db_path: string, location of sqllite db, ie './AlternativeData/reddit_test.db'
    '''

    start_datetime = datetime.strptime(start_datetime, '%Y-%m-%d')
    end_datetime = datetime.strptime(end_datetime, '%Y-%m-%d')

    daterange = pd.date_range(start_datetime, end_datetime, freq=freq)
 
    for tstmp in daterange:
        start_epoch = int(tstmp.timestamp())
        end_epoch = int((tstmp + pd.Timedelta(freq)).timestamp())

        @Timer(text="### Submissions fetched in {:.2f} seconds", logger=logging.info)
        def fetch_batch_submissions():
            print(f'Processing.. start: {tstmp} end: {(tstmp + pd.Timedelta(freq))}')

            submissions = api.search_submissions(
                after=start_epoch,
                before=end_epoch,
                subreddit=subreddits,
                # filter=fields_list,
                limit=None
            )

            results = list(submissions)

            return results

        # temp_list = []
        
        @Timer(text="### Submissions appended in {:.2f} seconds", logger=logging.info)
        def append_bulk_submissions(results):
            for res in results:
                try:
                    praw_submission_values = {
                        'praw_fullname':res.fullname,
                        'praw_id':res.id,
                        'praw_author':str(res.author),
                        'praw_created_utc':datetime.fromtimestamp(int(res.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
                        'praw_subreddit':res.subreddit.display_name,
                        'praw_subreddit_id': res.subreddit_id,
                        'praw_title':res.title,
                        'praw_selftext':res.selftext,
                        'praw_permalink':res.permalink,
                        'praw_url':res.url,
                        'praw_num_comments':res.num_comments,
                        'praw_score':res.score,
                        'praw_ups':res.ups,
                        'praw_upvote_ratio':res.upvote_ratio,
                        'praw_comment_ids':str(list(res._comments_by_id))
                    }

                    # temp_list.append(res.subreddit.display_name)

                    reddit_sql.insert_new_praw_submission(praw_submission_values, db=db_path)

                except Exception as e:
                    message = f'##### The following exception occurred {e} #####'
                    if logger is not None:
                        logger.info(message)
                    else:
                        print(e)
                    continue

        results = fetch_batch_submissions()
        append_bulk_submissions(results)


if __name__ == "__main__":

    import config
    import argparse
    # import logging
    from datetime import datetime
    import praw
    from psaw import PushshiftAPI

    starting_time = datetime.now().isoformat()

    parser = argparse.ArgumentParser()
    parser.add_argument('-sd', '--start_datetime', help='Date to start fetching', required=True)
    parser.add_argument('-ed', '--end_datetime', help='Date to end fetching', required=True)
    parser.add_argument('-db', '--db_path', help='DB file path where data is stored', required=True)
    parser.add_argument('-f', '--freq', help='Time frequency (such as 3H, 1D etc). Determines time batches for querying subreddit data', required=True)
    parser.add_argument('-subr', '--subreddits', nargs='+', help='list of subreddit to retrieve data for', required=True)

    args = parser.parse_args()

    print(args)

    # assign parsed variables
    start_datetime = args.start_datetime
    end_datetime = args.end_datetime
    db_path = args.db_path
    freq = args.freq
    subreddits = args.subreddits

    # instanciate logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger_name = f'Reddit data fetching logger - {starting_time}'
    logger.addHandler(logging.FileHandler(f'{config.directory_path}/StratTest/Logging/{logger_name}.log'))

    logger.info(f'Script started at {starting_time} with inputs: {args}')

    reddit = praw.Reddit(
        client_id=config.reddit_personal_use_script,
        client_secret=config.reddit_secret,
        user_agent="rlt_bot",
    )

    api = PushshiftAPI(reddit)

    fetch_submissions(api, start_datetime, end_datetime, freq, subreddits, db_path, logger=logger)

    print(Timer.timers)