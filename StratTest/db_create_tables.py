import psycopg2

def create_tables(config_parameters):
    commands = (
        """
        CREATE TABLE IF NOT EXISTS bot_bots_tbl (
                bot_id VARCHAR(36) PRIMARY KEY,
                bot_pair VARCHAR(10) NOT NULL,
                bot_start_date TIMESTAMP NOT NULL,
                bot_end_date TIMESTAMP,
                bot_strategy VARCHAR(255) NOT NULL,
                bot_strategy_parameters JSON,
                bot_stop_loss NUMERIC,
                bot_freq VARCHAR(30) NOT NULL,
                bot_exchange VARCHAR(30)
        )
        """,
        """ CREATE TABLE IF NOT EXISTS bot_order_book_snaps_tbl (
                ob_id SERIAL PRIMARY KEY,
                ob_bot_id VARCHAR(36),
                ob_timestamp TIMESTAMP NOT NULL,
                ob_open NUMERIC,
                ob_high NUMERIC,
                ob_low NUMERIC,
                ob_close NUMERIC,
                ob_action TEXT,
                ob_position INTEGER,
                ob_stop_loss_price NUMERIC,
                ob_strategy_signals JSON,
                FOREIGN KEY (ob_bot_id)
                    REFERENCES bot_bots_tbl (bot_id)
                    ON DELETE CASCADE
                )
        """,
        """
        CREATE TABLE IF NOT EXISTS bot_orders_tbl (
                order_id SERIAL PRIMARY KEY,
                order_bot_id VARCHAR(36),
                order_timestamp_placed TIMESTAMP NOT NULL,
                order_price_placed NUMERIC NOT NULL,
                order_quantity_placed NUMERIC NOT NULL,
                order_direction TEXT,
                order_status TEXT,
                order_ob_bid_price NUMERIC,
                order_ob_ask_price NUMERIC,
                order_ob_bid_size NUMERIC,
                order_ob_ask_size NUMERIC,
                order_exchange_trade_id TEXT,
                order_timestamp_filled TIMESTAMP,
                order_price_filled NUMERIC,
                order_quantity_filled NUMERIC,
                FOREIGN KEY (order_bot_id)
                    REFERENCES bot_bots_tbl (bot_id)
                    ON DELETE CASCADE
        )
        """
    )

    conn = None
    try:
        # read the connection parameters
        # connect to the PostgreSQL server
        conn = psycopg2.connect(**config_parameters)
        cur = conn.cursor()
        # create table one by one
        for command in commands:
            cur.execute(command)
        # close communication with the PostgreSQL database server
        cur.close()
        # commit the changes
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()


if __name__ == '__main__':
    import sys, os
    p = os.path.abspath('.')
    sys.path.append(p)

    import config
    config_parameters = config.pg_db_configuration(location='local')
    create_tables(config_parameters)