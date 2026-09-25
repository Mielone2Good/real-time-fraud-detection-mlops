import argparse
import os

import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--csv-path", type=str, default=os.getenv("CREDITCARD_CSV_PATH", "data/raw_data/creditcard.csv"))
parser.add_argument("--min-age", type=int, default=60, help="Label only transactions older than this many seconds")
args = parser.parse_args()

labels = pd.read_csv(args.csv_path, usecols=["Class"])["Class"]

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    database=os.getenv("POSTGRES_DB", "fraud_detection"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "postgres")
)

with conn, conn.cursor() as cursor:
    cursor.execute(
        "SELECT DISTINCT transaction_id FROM transactions "
        "WHERE isreallyfraud IS NULL AND timestamp < now() - make_interval(secs => %s)",
        (args.min_age,)
    )
    transaction_ids = [row[0] for row in cursor.fetchall()]
    for transaction_id in transaction_ids:
        cursor.execute(
            "UPDATE transactions SET isreallyfraud = %s WHERE transaction_id = %s",
            (int(labels[int(float(transaction_id))]), transaction_id)
        )

conn.close()
print(f"Labeled {len(transaction_ids)} transactions")
