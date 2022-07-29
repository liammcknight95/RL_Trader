import psycopg2
import pandas as pd

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
        print("Database error, record not appended: ", error)

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
            bot_stop_loss_pctg,
            bot_stop_loss_type,
            bot_freq,
            bot_exchange,
            bot_script_pid,
            bot_container_id,
            bot_container_name
        ) 
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
    """
    execute_db_commands(sql, fields, config_parameters)
    return sql


def update_bots_table(fields, config_parameters):
    sql = """
        UPDATE bot_bots_tbl
            SET bot_owned_ccy_end_position = %s, 
                bot_end_date = %s
            WHERE bot_id = %s
    """
    execute_db_commands(sql, fields, config_parameters)
    return sql

def insert_order_book_bars_table(fields, config_parameters):
    sql = """ 
        INSERT INTO bot_order_book_bars_tbl(
            bar_bot_id,
            bar_record_timestamp,
            bar_time,
            bar_open,
            bar_high,
            bar_low,
            bar_close,
            bar_volume,
            bar_action,
            bar_in_position,
            bar_stop_loss_price,
            bar_strategy_signal,
            bar_param_1,
            bar_param_2,
            bar_param_3,
            bar_param_4
        ) 
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
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
            order_quantity_filled,
            order_price_filled,
            order_fee
        ) 
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
    """
    execute_db_commands(sql, fields, config_parameters)
    return sql


def update_single_order_table(fields, config_parameters):
    sql = """
        UPDATE bot_orders_tbl
            SET order_status = %s, 
                order_trades = %s, 
                order_quantity_filled = %s,
                order_price_filled = %s,
                order_fee = %s
            WHERE order_bot_id = %s AND order_exchange_trade_id = %s
    """
    execute_db_commands(sql, fields, config_parameters)
    return sql


# TODO update all pending orders when cancelling the bot - update_pending_orders_table in progress
# update orders when cancelled by the strategy 
def update_pending_orders_table(fields, config_parameters):
    sql = """
        UPDATE bot_orders_tbl
            SET order_status = %s, 
                order_trades = %s, 
                order_quantity_filled = %s
            WHERE 
                order_bot_id = %s AND
                (order_status = 'dormant' OR order_status = 'partialled')
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

# TODO update order quantity filled

## SELECT QUERIES
def select_all_bot_orders(bot_id, order_statuses, config_parameters):
    sql = f"""
    SELECT 
        order_id, 
        order_bot_id,
        order_exchange_trade_id,
        order_timestamp_placed,
        order_status,
        order_price_filled,
        order_quantity_filled,
        order_direction,
        order_price_placed,
        order_ob_ask_price,
        order_ob_bid_price,
        order_fee
    FROM 
        bot_orders_tbl
    WHERE 
        order_bot_id = '{bot_id}' AND
        order_status IN {order_statuses}
        --(order_status = 'dormant' OR order_status = 'partialled')
    """

    conn = psycopg2.connect(**config_parameters)
    data = pd.read_sql(sql, conn)
    return data

def select_bot_current_exposure(bot_id, config_parameters):
    sql = f"""
    SELECT 
        SUM(CASE 
            WHEN order_direction='buy' THEN order_quantity_filled * 1 
            WHEN order_direction='sell' THEN order_quantity_filled * -1  
        END) AS order_net_filled	
        
    FROM 
        bot_orders_tbl
    WHERE 
        order_bot_id = '{bot_id}'
    """

    conn = psycopg2.connect(**config_parameters)
    data = pd.read_sql(sql, conn)
    return data.values[0][0]
    

def select_single_bot(config_parameters, bot_id=''):
    ''' query that select bots, either all or single one '''

    if len(bot_id)>0:
        where_statement = f"WHERE bot_id = '{bot_id}'"
    else:
        where_statement = ""

    sql = f""" 
    SELECT * FROM bot_bots_tbl {where_statement}
    """

    conn = psycopg2.connect(**config_parameters)
    data = pd.read_sql(sql, conn)
    return data


def select_all_active_bots(config_parameters):
    ''' query that selects all active bots, having a null end of bot time '''

    sql = ''' SELECT * FROM bot_bots_tbl WHERE bot_end_date IS NULL '''

    conn = psycopg2.connect(**config_parameters)
    data = pd.read_sql(sql, conn)
    return data


def select_active_bots_status(config_parameters):
    ''' query that selects all active bots grouped by health status, to flag 
        last valid update as well as any malfunctioning '''

    sql = ''' 
        SELECT 
            bots.bot_id,
            bots.bot_container_name,
            bots.bot_exchange,
            bots.bot_pair,
            bots.bot_owned_ccy_start_position,
            bots.bot_strategy,
            bots.bot_freq,
            bots.bot_stop_loss_pctg,
            bots.bot_stop_loss_type,
            bots.bot_strategy_parameters,
			health.health_status,
			health.health_status_error,
			health.last_update
        FROM bot_bots_tbl as bots
			LEFT JOIN (
				SELECT    
					health_status_bot_id,
					health_status,
            		health_status_error,
					MAX(health_status_timestamp) as last_update
				FROM
					bot_health_status_tbl
				GROUP BY
					health_status_bot_id,
					health_status,
            		health_status_error				
			) health ON health.health_status_bot_id = bots.bot_id
        WHERE 
            bots.bot_end_date is Null
        ORDER BY 
            bots.bot_start_date DESC, 
            health.last_update DESC
    '''

    conn = psycopg2.connect(**config_parameters)
    data = pd.read_sql(sql, conn)
    if data.shape[0]>0:
        try:
            data['last_update'] = data['last_update'].dt.tz_convert('Europe/London')
        except:
            # not a valid datetime yet
            data['last_update'] = data['last_update']
    return data


def select_running_orders(config_parameters):
    ''' query that selects orders belonging to active bots or recently terminated ones '''

    sql = ''' 
        SELECT * 
        FROM bot_orders_tbl AS orders, bot_bots_tbl AS bots
        WHERE orders.order_bot_id = bots.bot_id
            AND (
                bots.bot_end_date IS NULL 
                OR bots.bot_end_date > (NOW() - INTERVAL '1 days')
            )
        ORDER BY order_timestamp_placed DESC
        ;'''

    conn = psycopg2.connect(**config_parameters)
    data = pd.read_sql(sql, conn)
    return data


def order_filled_checked(exchange_trade_id, config_parameters):
    ''' query that checks if an existing order has been completely filled or not '''

    sql = f'''
        SELECT ABS(order_quantity_placed - order_quantity_filled) <0.0000001 
        FROM public.bot_orders_tbl
        WHERE order_exchange_trade_id = '{exchange_trade_id}'
    '''

    conn = psycopg2.connect(**config_parameters)
    data = pd.read_sql(sql, conn)
    return data.values[0][0]


def order_placed_amount(exchange_trade_id, config_parameters):
    ''' query that pulls amount order placed'''

    sql = f''' 
        SELECT order_quantity_placed from bot_orders_tbl
        WHERE order_exchange_trade_id = '{exchange_trade_id}' '''


    conn = psycopg2.connect(**config_parameters)
    data = pd.read_sql(sql, conn)
    return data.values[0][0]


def select_bot_distinct_bars(bot_id, config_parameters):
    ''' query that returns the vary last update for each bar stored in the database per bot '''

    sql = f''' 
    SELECT DISTINCT ON (bar_time, bar_action) 
        bar_time, 
        bar_record_timestamp,
        bar_open,
        bar_high,
        bar_low,
        bar_close,
        bar_stop_loss_price,
        bar_action,
        bar_in_position,
        bar_strategy_signal,
        bar_param_1,
        bar_param_2,
        bar_param_3,
        bar_param_4
    FROM 
        bot_order_book_bars_tbl -- bar_time, bar_stop_loss_price
    WHERE 
        bar_bot_id = '{bot_id}' 
    ORDER BY 
        bar_time ASC, 
        bar_action ASC,
        bar_record_timestamp DESC
        
    '''


    conn = psycopg2.connect(**config_parameters)
    data = pd.read_sql(sql, conn)
    return data

# TODO update existing order:
# update if partially or totally filled - amount
# update if cancelled - status
# json field with update history - {timestamp:reason} - can be used to check validity of orders against order book data
# check index time