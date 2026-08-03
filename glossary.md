# InsightPilot business glossary

Fifteen KPI definitions for the Olist e-commerce dataset (PRD.md F5). Each
entry is one retrieval chunk: a `## <KPI name>` heading plus a definition
and an exact formula referencing real `olist` schema tables/columns (see
`scripts/seed.py` for the authoritative column list). Formulas are written
as plain-English SQL fragments, not runnable SQL — `generate_sql()`'s LLM
call turns them into real `SELECT` statements using the schema context
retrieved alongside this glossary context.

## Revenue

Total money collected from customers for product sales, excluding
shipping cost.

Formula: `SUM(olist.order_items.price)`, optionally restricted to order
items whose order has `olist.orders.order_status = 'delivered'` (join
`olist.order_items.order_id` to `olist.orders.order_id`).

## Average Order Value (AOV)

The average amount, in product-price terms, a customer pays per order.

Formula: `SUM(olist.order_items.price) / COUNT(DISTINCT olist.order_items.order_id)`.

## Repeat Purchase Rate

The share of customers who have placed more than one order. Note:
`olist.customers.customer_id` is a per-order identifier;
`olist.customers.customer_unique_id` identifies the same real person
across multiple orders — this specific distinction (unique person vs.
per-order record) only matters for repeat-purchase/churn-style questions
below; a plain "how many customers" or "customers per state" question
should still use `olist.customers.customer_id` (or `COUNT(*)` on
`olist.customers`, one row per customer record) unless it explicitly asks
about unique/repeat people.

Formula (repeat purchase rate specifically): count distinct
`customer_unique_id` values with `COUNT(DISTINCT olist.orders.order_id) >
1` (join `olist.customers.customer_id` to `olist.orders.customer_id`,
group by `customer_unique_id`), divided by the total count of distinct
`customer_unique_id` values.

## Average Delivery Time

The average number of days between an order's purchase and its actual
delivery to the customer.

Formula: `AVG(olist.orders.order_delivered_customer_date -
olist.orders.order_purchase_timestamp)`, restricted to rows where
`order_delivered_customer_date IS NOT NULL`.

## On-Time Delivery Rate

The share of delivered orders that arrived on or before Olist's own
estimated delivery date.

Formula: `COUNT(*) WHERE order_delivered_customer_date <=
order_estimated_delivery_date` divided by `COUNT(*) WHERE
order_delivered_customer_date IS NOT NULL`, both from `olist.orders`.

## Average Review Score

The mean customer satisfaction rating across all submitted reviews, on a
1-5 scale.

Formula: `AVG(olist.order_reviews.review_score)`.

## Low Review Rate

The share of reviews rated 1 or 2 (dissatisfied customers) out of all
reviews.

Formula: `COUNT(*) WHERE olist.order_reviews.review_score <= 2` divided by
`COUNT(*)` from `olist.order_reviews`.

## Churn Proxy

Olist has no subscription or renewal event, so churn is approximated as
the number of days since a customer's most recent order — a large gap
suggests the customer has gone inactive.

Formula: `CURRENT_DATE - MAX(olist.orders.order_purchase_timestamp)`,
grouped by `olist.customers.customer_unique_id` (join
`olist.customers.customer_id` to `olist.orders.customer_id`).

## Freight Ratio

Shipping cost as a fraction of product price — how much of an order's
total cost is consumed by delivery.

Formula: `SUM(olist.order_items.freight_value) /
SUM(olist.order_items.price)`.

## Average Items per Order

The average number of order-line items per distinct order.

Formula: `COUNT(olist.order_items.order_item_id) / COUNT(DISTINCT
olist.order_items.order_id)`.

## Order Cancellation Rate

The share of orders whose status is `'canceled'`, out of all orders.

Formula: `COUNT(*) WHERE olist.orders.order_status = 'canceled'` divided
by `COUNT(*)` from `olist.orders`.

## Order Approval Time

The average time between an order's purchase and its payment approval.

Formula: `AVG(olist.orders.order_approved_at -
olist.orders.order_purchase_timestamp)`, restricted to rows where
`order_approved_at IS NOT NULL`.

## Average Payment Installments

The average number of installments customers choose when paying for an
order.

Formula: `AVG(olist.order_payments.payment_installments)`.

## Active Seller Count

The number of distinct sellers who have sold at least one order item.

Formula: `COUNT(DISTINCT olist.order_items.seller_id)`.

## Top Product Category

The product category with the most orders — answers "top/best-selling
category by number of orders" questions. "By number of orders" means
distinct orders, not order-line-item rows: an order with two items from
the same category must count once, not twice.

Formula: join `olist.order_items.product_id` to
`olist.products.product_id`, group by
`olist.products.product_category_name`, rank by
`COUNT(DISTINCT olist.order_items.order_id)` descending. Category names
in `olist.products.product_category_name` are Portuguese; only join to
`olist.product_category_name_translation` for an English label if the
question specifically asks for one, since translating changes the
category's label but never its ranking or count.

## Payment Type Mix

The distribution of how customers pay (credit card, boleto, voucher,
debit card), by count of payments.

Formula: `COUNT(*)` from `olist.order_payments`, grouped by
`olist.order_payments.payment_type`, ordered by count descending.
