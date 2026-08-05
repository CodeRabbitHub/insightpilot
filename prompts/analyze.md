# analyze v1

You are analyzing the result of a SQL query already run against a
PostgreSQL analytics database called `olist`, an e-commerce dataset, to
answer a business question in plain English.

You are given the original question, the executed SQL, and a sample of
its result rows (as JSON). The sample may be smaller than the query's
total row count -- if so, that is noted below; ground your analysis in
the sample's actual values, and say so in the explanation if the sample
is partial.

Task: write a JSON object with four fields:
- `summary`: one sentence that directly answers the question using the
  actual data.
- `explanation`: a short paragraph grounded in the sample's actual
  values, describing what the query did and why the result answers the
  question.
- `chart_spec`: a JSON object proposing a reasonable chart type and
  axis/field mapping for this result shape (e.g. bar, line, pie -- pick
  whatever best fits the columns and question). No fixed schema is
  required beyond being a JSON object; if the result isn't meaningfully
  chartable (e.g. a single scalar value), return a minimal object rather
  than fabricate axes that don't exist in the data.
- `follow_ups`: a JSON array of 3 to 5 natural next questions a user
  could ask, each answerable from the same `olist` schema.

Respond with ONLY a JSON object of this exact shape, no other text before
or after it:
{"summary": "...", "explanation": "...", "chart_spec": {...}, "follow_ups": ["...", "..."]}

Question: $question

Executed SQL:
$sql

Result sample ($sample_size of $row_count total row(s), as JSON):
$row_sample
