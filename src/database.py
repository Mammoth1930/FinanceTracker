"""
This file contains the code which is used to setup and manipulate the SQLite3
database used to store all of the financial data for the dashboard.
"""

import sqlite3
import pandas as pd
from threading import Lock

# SQLite3 database file name
DB_FILE = "finance.db"

# Create a connection to the database
DB_CONN = sqlite3.connect(DB_FILE, check_same_thread=False)

# Write lock
WRITE = Lock()

def db_init():
    """
    Creates the database tables if they don't already exist.
    """

    with WRITE:
        cur = DB_CONN.cursor()

        # Create the Accounts table
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS Accounts (
                id TEXT,
                displayName TEXT,
                accountType TEXT,
                ownershipType TEXT,
                balance INTEGER,
                created TEXT,
                deleted INTEGER DEFAULT 0,
                PRIMARY KEY (id)
            )
            '''
        )

        # Create the Transactions table
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS Transactions (
                id TEXT,
                status TEXT,
                rawText TEXT,
                description TEXT,
                message TEXT,
                isCategorizable INTEGER,
                held INTEGER,
                heldAmount INTEGER,
                roundUpAmount INTEGER,
                boostProportion INTEGER,
                cashbackDesc TEXT,
                cashbackAmount INTEGER,
                amount INTEGER,
                foreignCurrency TEXT,
                foreignAmount INTEGER,
                cardPurchaseMethod TEXT,
                cardNumberSuffix TEXT,
                settledAt TEXT,
                createdAt TEXT,
                account TEXT,
                transferAccount TEXT,
                category TEXT,
                parentCategory TEXT,
                PRIMARY KEY (id),
                FOREIGN KEY (account) REFERENCES Accounts(id),
                FOREIGN KEY (transferAccount) REFERENCES Accounts(id)
            )
            '''
        )

        # Create the Tags table
        # DB_CONN.execute(
        #     '''
        #     CREATE TABLE IF NOT EXISTS Tags (
        #         id TEXT,
        #         transaction TEXT,
        #         PRIMARY KEY (id),
        #         FOREIGN KEY (transaction) REFERENCES Transactions(id)
        #     )
        #     '''
        # )

        DB_CONN.commit()
        cur.close()


def write_to_db(table:str, data: pd.DataFrame):
    """
    Performs a database insert operation on a specified table.

    Params:
        table: A string representing the name of the table the data is to be
            inserted into. This can be the name of a table which does not exist,
            however the function is intended to be used to append data to one of
            the preexisting tables.

        data: A Pandas DataFrame or Series containing the data to be inserted into
            the specified table. The data should be formatted with the same schema
            as the table it is being inserted into.
    """
    with WRITE:
        data.to_sql(table, DB_CONN, index=False, if_exists='append')

def read_database(query:str, params: list|None=None) -> pd.DataFrame:
    """
    Executes an SQL SELECT query on the database and returns the result as a Pandas
    DataFrame. Expects the query to be a part of the DQL.

    Params:
        query: A string representing the SQL query to be performed on the database.
        params: A list of parameter values to be inserted into the SQL query.

    Returns:
        pd.DataFrame: Result of the SQL query.
    """

    return pd.read_sql_query(query, DB_CONN, params=params)

def execute_query(query: str) -> None:
    """
    Executes a DML or DDL SQL query on the database.

    Params:
        query: A string representing the SQL query to be performed on the database.
    """
    
    with WRITE:
        cur = DB_CONN.cursor()
        cur.execute(query)
        DB_CONN.commit()
        cur.close()

def upsert_accounts(data: pd.DataFrame):
    """
    Changes the Accounts table to reflect the provided state.

    Params:
        data: A Pandas DataFrame with the same schema as the Accounts table. This
            DataFrame should reflect the most current state of accounts.
    """

    existing_accnts = read_database('SELECT id FROM Accounts')

    for i, row in data.iterrows():
        # If the account is already in the database we need to update
        if row['id'] in existing_accnts['id'].values:
            execute_query(
                f'''
                UPDATE Accounts
                SET displayName = "{row['displayName']}",
                    balance = {row['balance']}
                WHERE id = "{row['id']}"
                '''
            )

            # Drop the existing account so we can check for deleted accounts
            existing_accnts.drop(
                existing_accnts.index[existing_accnts['id'] == row['id']].tolist(),
                inplace=True
            )
            continue

        # Otherwise this is a new account and we need to insert it
        execute_query(
            f'''
            INSERT INTO Accounts (id, displayName, accountType, ownershipType, balance, created)
            VALUES ("{row['id']}", "{row['displayName']}", "{row['accountType']}", "{row['ownershipType']}", {row['balance']}, "{row['created']}")
            '''
        )

    # Any accounts left in existing_accounts must have been deleted
    for i, row in existing_accnts.iterrows():
        execute_query(
            f'''
            UPDATE Accounts
            SET deleted = 1,
                balance = 0
            WHERE id = "{row['id']}"
            '''
        )

def upsert_transactions(data: pd.DataFrame, new: bool) -> None:
    """
    Upserts the Transaction table in the database to reflect changes to transactions
    in the provided DataFrame.

    Params:
        data: A DataFrame containing the transactions to be upserted to the
            transactions table in the database.

        new: A boolean flag which is True if all the transactions provided are new
            transactions which don't already exist in the Transactions table and
            False if all the transactions provided already exist in the table.

    Require:
        data: Must contain only new or not new transactions, there cannot be a
            mixture of transactions which do and don't exist in the database.
    """

    # New transactions we can simply insert
    if new:
        write_to_db('Transactions', data)
        return
    
    # If the transactions are existing we need to update
    for i, row in data.iterrows():
        execute_query(
            f'''
            UPDATE Transactions
            SET status = "{row['status']}",
                cashbackDesc = "{row['cashbackDesc']}",
                cashbackAmount = "{row['cashbackAmount']}",
                settledAt = "{row['settledAt']}",
                category = "{row['category']}",
                parentCategory = "{row['parentCategory']}"
            WHERE id = "{row['id']}"
            '''
        )