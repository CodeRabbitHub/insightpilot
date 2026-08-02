# Olist dataset

Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
on Kaggle. Downloading it requires a (free) Kaggle account — this is a
manual, out-of-band step; v1 does not script the Kaggle API download.

Download the dataset and place these 9 files directly in this `data/`
directory (not a subfolder):

- `olist_customers_dataset.csv`
- `olist_geolocation_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_order_payments_dataset.csv`
- `olist_order_reviews_dataset.csv`
- `olist_orders_dataset.csv`
- `olist_products_dataset.csv`
- `olist_sellers_dataset.csv`
- `product_category_name_translation.csv`

Note: `product_category_name_translation.csv` is the one file without an
`olist_` prefix, and ships with a UTF-8 BOM — `scripts/seed.py` handles
both transparently.

These CSVs are gitignored (`data/*.csv`) — do not commit them.

Once the files are in place, run `python scripts/seed.py` to load them.
