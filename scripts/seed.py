import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def require_env(name):
    try:
        return os.environ[name]
    except KeyError:
        raise SystemExit(
            f"Missing required env var {name!r}. Copy .env.example to .env "
            "and fill in real values."
        )

# (csv filename, table name, column DDL) — DDL column order must match the
# CSV header order exactly: COPY ... HEADER true matches by position, not
# by name.
TABLES = [
    (
        "olist_customers_dataset.csv",
        "customers",
        """
        customer_id VARCHAR PRIMARY KEY,
        customer_unique_id VARCHAR NOT NULL,
        customer_zip_code_prefix VARCHAR,
        customer_city VARCHAR,
        customer_state VARCHAR(2)
        """,
    ),
    (
        "olist_geolocation_dataset.csv",
        "geolocation",
        """
        geolocation_zip_code_prefix VARCHAR,
        geolocation_lat DOUBLE PRECISION,
        geolocation_lng DOUBLE PRECISION,
        geolocation_city VARCHAR,
        geolocation_state VARCHAR(2)
        """,
    ),
    (
        "olist_order_items_dataset.csv",
        "order_items",
        """
        order_id VARCHAR NOT NULL,
        order_item_id INTEGER NOT NULL,
        product_id VARCHAR,
        seller_id VARCHAR,
        shipping_limit_date TIMESTAMP,
        price NUMERIC(10,2),
        freight_value NUMERIC(10,2),
        PRIMARY KEY (order_id, order_item_id)
        """,
    ),
    (
        "olist_order_payments_dataset.csv",
        "order_payments",
        """
        order_id VARCHAR NOT NULL,
        payment_sequential INTEGER,
        payment_type VARCHAR,
        payment_installments INTEGER,
        payment_value NUMERIC(10,2)
        """,
    ),
    (
        "olist_order_reviews_dataset.csv",
        "order_reviews",
        """
        review_id VARCHAR NOT NULL,
        order_id VARCHAR NOT NULL,
        review_score INTEGER,
        review_comment_title TEXT,
        review_comment_message TEXT,
        review_creation_date TIMESTAMP,
        review_answer_timestamp TIMESTAMP
        """,
    ),
    (
        "olist_orders_dataset.csv",
        "orders",
        """
        order_id VARCHAR PRIMARY KEY,
        customer_id VARCHAR NOT NULL,
        order_status VARCHAR,
        order_purchase_timestamp TIMESTAMP,
        order_approved_at TIMESTAMP,
        order_delivered_carrier_date TIMESTAMP,
        order_delivered_customer_date TIMESTAMP,
        order_estimated_delivery_date TIMESTAMP
        """,
    ),
    (
        "olist_products_dataset.csv",
        "products",
        """
        product_id VARCHAR PRIMARY KEY,
        product_category_name VARCHAR,
        product_name_lenght INTEGER,
        product_description_lenght INTEGER,
        product_photos_qty INTEGER,
        product_weight_g INTEGER,
        product_length_cm INTEGER,
        product_height_cm INTEGER,
        product_width_cm INTEGER
        """,
    ),
    (
        "olist_sellers_dataset.csv",
        "sellers",
        """
        seller_id VARCHAR PRIMARY KEY,
        seller_zip_code_prefix VARCHAR,
        seller_city VARCHAR,
        seller_state VARCHAR(2)
        """,
    ),
    (
        "product_category_name_translation.csv",
        "product_category_name_translation",
        """
        product_category_name VARCHAR,
        product_category_name_english VARCHAR
        """,
    ),
]


def connect(user_env="POSTGRES_USER", password_env="POSTGRES_PASSWORD"):
    return psycopg2.connect(
        host=require_env("POSTGRES_HOST"),
        port=require_env("POSTGRES_PORT"),
        dbname=require_env("POSTGRES_DB"),
        user=require_env(user_env),
        password=require_env(password_env),
    )


def load_table(cur, csv_name, table_name, ddl):
    csv_path = DATA_DIR / csv_name
    cur.execute(f"DROP TABLE IF EXISTS olist.{table_name} CASCADE;")
    cur.execute(f"CREATE TABLE olist.{table_name} ({ddl});")
    # utf-8-sig strips the BOM on product_category_name_translation.csv and
    # is a no-op for the other 8 plain-UTF-8 files.
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        cur.copy_expert(
            f"COPY olist.{table_name} FROM STDIN "
            "WITH (FORMAT csv, HEADER true, NULL '')",
            f,
        )
    cur.execute(f"SELECT COUNT(*) FROM olist.{table_name};")
    return cur.fetchone()[0]


def ensure_ro_role(cur, owner, ro_user, ro_password):
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", (ro_user,))
    if cur.fetchone() is None:
        cur.execute(f'CREATE ROLE "{ro_user}" LOGIN PASSWORD %s;', (ro_password,))
    cur.execute(f'GRANT USAGE ON SCHEMA olist TO "{ro_user}";')
    cur.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA olist TO "{ro_user}";')
    # Tables are dropped and recreated on every run (see load_table), which
    # would otherwise wipe olist_ro's grants on the next seed — default
    # privileges reapply SELECT automatically to tables the owner creates.
    cur.execute(
        f'ALTER DEFAULT PRIVILEGES FOR ROLE "{owner}" IN SCHEMA olist '
        f'GRANT SELECT ON TABLES TO "{ro_user}";'
    )


def main():
    owner = require_env("POSTGRES_USER")
    ro_user = require_env("OLIST_RO_USER")
    ro_password = require_env("OLIST_RO_PASSWORD")

    conn = connect()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute("CREATE SCHEMA IF NOT EXISTS olist;")

            for csv_name, table_name, ddl in TABLES:
                count = load_table(cur, csv_name, table_name, ddl)
                print(f"  olist.{table_name}: {count} rows")

            ensure_ro_role(cur, owner, ro_user, ro_password)

        conn.commit()
        print("Seed complete.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
