import psycopg2

def insert_bots_table():
    sql = """ 
        INSERT INTO bot_bots_tbl(
            bot_id,
            bot_pair,
            bot_start_date,
            bot_end_date,
            bot_strategy,
            bot_strategy_parameters,
            bot_stop_loss,
            bot_freq,
            bot_exchange
        ) 
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s) 
    """

    #TODO execute command in here
    return sql

def insert_order_book_snaps_table():
    sql = """ 
        INSERT INTO bot_order_book_snaps_tbl(
            ob_id,
            ob_bot_id,
            ob_timestamp,
            ob_open,
            ob_high,
            ob_low,
            ob_close,
            ob_action,
            ob_position,
            ob_stop_loss_price,
            ob_strategy_signals
        ) 
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
    """
    return sql

def insert_orders_table():
    sql = """ 
        INSERT INTO bot_orders_tbl(
            order_id,
            order_bot_id,
            order_timestamp_placed,
            order_price_placed,
            order_quantity_placed,
            order_direction,
            order_status,
            order_ob_bid_price,
            order_ob_ask_price,
            order_ob_bid_size,
            order_ob_ask_size,
            order_exchange_trade_id,
            order_timestamp_filled,
            order_price_filled,
            order_quantity_filled
        ) 
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
    """
    return sql


def execute_db_commands(sql, fields, config_parameters):
    """ Template to execute postgres commands 
    commands: string containing a SQL statements 
    fields: tuple containing query fields
    """

    conn = None
    try:
        # read the connection parameters
        # connect to the PostgreSQL server
        conn = psycopg2.connect(**config_parameters)
        cur = conn.cursor()

        # for command in commands:
        cur.execute(sql, fields)
        # close communication with the PostgreSQL database server
        cur.close()
        # commit the changes
        conn.commit()

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

    except psycopg2.IntegrityError:
        # in case pf key violation
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()