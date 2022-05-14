import psycopg2

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

    # TODO add logging of database operation results here
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

    except psycopg2.IntegrityError:
        # in case pf key violation
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()


def insert_bots_table(fields, config_parameters):
    sql = """ 
        INSERT INTO bot_bots_tbl(
            bot_id,
            bot_pair,
            bot_owned_ccy_start_position,
            bot_owned_ccy_end_position,
            bot_start_date,
            bot_end_date,
            bot_strategy,
            bot_strategy_parameters,
            bot_stop_loss_type,
            bot_stop_loss_pctg,
            bot_freq,
            bot_exchange
        ) 
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
    """
    execute_db_commands(sql, fields, config_parameters)
    return sql


def insert_order_book_bars_table(fields, config_parameters):
    sql = """ 
        INSERT INTO bot_order_book_bars_tbl(
            ob_bot_id,
            ob_record_timestamp,
            ob_bar_time,
            ob_open,
            ob_high,
            ob_low,
            ob_close,
            ob_action,
            ob_in_position,
            ob_stop_loss_price,
            ob_strategy_signal
        ) 
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,  %s) 
    """
    execute_db_commands(sql, fields, config_parameters)
    return sql


def insert_orders_table(fields, config_parameters):
    sql = """ 
        INSERT INTO bot_orders_tbl(
            order_id,
            order_bot_id,
            order_timestamp_placed,
            order_price_placed,
            order_quantity_placed,
            order_direction,
            order_exchange_type,
            order_status,
            order_ob_bid_price,
            order_ob_ask_price,
            order_ob_bid_size,
            order_ob_ask_size,
            order_exchange_trade_id,
            order_trades,
            order_quantity_filled
        ) 
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
    """
    execute_db_commands(sql, fields, config_parameters)
    return sql


def insert_health_status_table(fields, config_parameters):
    sql = """ 
        INSERT INTO bot_health_status_tbl(
            health_status_bot_id,
            health_status_timestamp,
            health_status,
            health_status_error
        ) 
        VALUES(%s, %s, %s, %s) 
    """
    execute_db_commands(sql, fields, config_parameters)
    return sql


# TODO update existing order:
# update if partially or totally filled - amount
# update if cancelled - status
# json field with update history - {timestamp:reason} - can be used to check validity of orders against order book data
# check index time