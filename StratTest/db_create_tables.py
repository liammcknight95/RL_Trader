import psycopg2

def create_tables(config_parameters):
    commands = (
        """
        CREATE TABLE IF NOT EXISTS bot_bots_tbl (
                bot_id VARCHAR(40) PRIMARY KEY,
                bot_pair VARCHAR(10) NOT NULL,
                bot_owned_ccy_start_position NUMERIC NOT NULL,
                bot_owned_ccy_end_position NUMERIC,
                bot_start_date TIMESTAMP NOT NULL,
                bot_end_date TIMESTAMP,
                bot_strategy VARCHAR(255) NOT NULL,
                bot_strategy_parameters JSON,
                bot_stop_loss_pctg NUMERIC,
                bot_stop_loss_type VARCHAR(30),
                bot_freq VARCHAR(30) NOT NULL,
                bot_exchange VARCHAR(30) NOT NULL,
                bot_script_pid INTEGER NOT NULL
        )
        """,
        """ 
        CREATE TABLE IF NOT EXISTS bot_order_book_bars_tbl (
                bar_id SERIAL PRIMARY KEY,
                bar_bot_id VARCHAR(40),
                bar_record_timestamp TIMESTAMP NOT NULL,
                bar_time TIMESTAMP,
                bar_open NUMERIC,
                bar_high NUMERIC,
                bar_low NUMERIC,
                bar_close NUMERIC,
                bar_volume NUMERIC,
                bar_action TEXT,
                bar_in_position BOOLEAN,
                bar_stop_loss_price NUMERIC,
                bar_strategy_signal NUMERIC,
                FOREIGN KEY (bar_bot_id)
                    REFERENCES bot_bots_tbl (bot_id)
                    ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS bot_orders_tbl (
                order_id VARCHAR(42) PRIMARY KEY,
                order_bot_id VARCHAR(40),
                order_timestamp_placed TIMESTAMP NOT NULL,
                order_price_placed NUMERIC NOT NULL,
                order_quantity_placed NUMERIC NOT NULL,
                order_direction TEXT,
                order_exchange_type TEXT,
                order_status TEXT,
                order_ob_bid_price NUMERIC,
                order_ob_ask_price NUMERIC,
                order_ob_bid_size NUMERIC,
                order_ob_ask_size NUMERIC,
                order_exchange_trade_id TEXT,
                order_trades TEXT[],
                order_quantity_filled NUMERIC,
                order_price_filled NUMERIC,
                order_fee NUMERIC,
                FOREIGN KEY (order_bot_id)
                    REFERENCES bot_bots_tbl (bot_id)
                    ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS bot_health_status_tbl (
            health_status_id SERIAL PRIMARY KEY,
            health_status_bot_id VARCHAR(40),
            health_status_timestamp TIMESTAMP NOT NULL,
            health_status TEXT NOT NULL, 
            health_status_error TEXT,
            FOREIGN KEY (health_status_bot_id)
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