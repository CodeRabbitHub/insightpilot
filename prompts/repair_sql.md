# repair_sql v1

You are repairing a PostgreSQL `SELECT` statement that failed validation
or execution against the `olist` analytics database.

Task: given the original business question, the SQL that failed, and the
real error message, write exactly one corrected PostgreSQL `SELECT`
statement that fixes the problem and still answers the question.

Rules:
- Return exactly one `SELECT` statement. Never DDL, DML, or multiple
  statements separated by semicolons.
- Always reference tables using their full schema-qualified name,
  `olist.<table_name>`.
- Fix only what the error indicates is wrong; keep the rest of the failed
  SQL's intent where it still serves the question.

Respond with ONLY a JSON object of this exact shape, no other text before
or after it:
{"sql": "<the corrected SELECT statement>"}

Question: $question

Failed SQL:
$failed_sql

Error:
$error
