# table_description v1

You are documenting a PostgreSQL analytics table for a business
intelligence catalog. You are given the table's DDL and its columns
(name, type, primary/foreign-key flags, and up to 5 real sample values).

Write ONE paragraph, 3 to 6 sentences, in plain English, aimed at a
business analyst who has never seen the schema. Cover: what real-world
entity or event each row represents, the most important columns and what
they mean, and any relationship to other e-commerce tables that is
evident from foreign keys or naming. Do not restate the DDL verbatim. Do
not use markdown or bullet points.

Respond with ONLY a JSON object of this exact shape, no other text before
or after it:
{"description": "<the paragraph>"}

Table: olist.$table_name

DDL:
$ddl_summary

Columns:
$columns_context
