import re
import sys

from dotenv import load_dotenv

from app.catalog.sync import connect
from app.pipeline.generate_sql import generate_sql

load_dotenv()

# Lightweight sanity check, not a real SQL parser (sqlglot is out of scope
# for this slice). Good enough to catch a hallucinated table/column name
# without false-positiving on table aliases (FROM olist.orders o) or
# output aliases (COUNT(*) AS order_count).
SQL_STOPWORDS = {
    "select", "from", "where", "group", "by", "order", "limit", "join",
    "on", "as", "and", "or", "not", "in", "is", "null", "distinct",
    "asc", "desc", "inner", "left", "right", "outer", "full", "having",
    "count", "sum", "avg", "min", "max", "case", "when", "then", "else",
    "end", "between", "like", "exists", "union", "all", "true", "false",
    "olist", "over", "partition", "with", "cast", "coalesce",
}

_STRING_LITERAL_RE = re.compile(r"'[^']*'")
_DOTTED_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b")
_AS_ALIAS_RE = re.compile(r"\bAS\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.IGNORECASE)
_IMPLICIT_ALIAS_RE = re.compile(
    r"\bolist\.[A-Za-z_][A-Za-z0-9_]*\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.IGNORECASE
)
_IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


def _blank_spans(text, spans):
    chars = list(text)
    for start, end in spans:
        for i in range(start, end):
            chars[i] = " "
    return "".join(chars)


def check_references(sql, valid_tables, valid_columns):
    """Alias-aware sanity check for hallucinated table/column names.

    Not a real parser: doesn't verify an alias actually refers to the
    table it was assigned to, validates bare column tokens against the
    full cross-table column set rather than per-table, and only
    recognizes aliases via `AS <alias>` or `olist.<table> <alias>`
    adjacency -- a bare subquery alias like `(SELECT ...) sub` would be
    flagged as an unknown identifier. Good enough to catch an invented
    name without false-positiving on the aliases this project's prompt
    actually produces; full validation is the sqlglot slice's job.
    """
    text = _STRING_LITERAL_RE.sub(lambda m: " " * len(m.group(0)), sql)

    known_aliases = {match.group(1) for match in _AS_ALIAS_RE.finditer(text)}
    for match in _IMPLICIT_ALIAS_RE.finditer(text):
        candidate = match.group(1)
        if candidate.lower() not in SQL_STOPWORDS:
            known_aliases.add(candidate)

    failures = []
    dotted_spans = []
    for match in _DOTTED_RE.finditer(text):
        prefix, suffix = match.group(1), match.group(2)
        dotted_spans.append(match.span())
        if prefix.lower() == "olist":
            if suffix not in valid_tables:
                failures.append(f"olist.{suffix}")
        elif suffix not in valid_columns:
            failures.append(f"{prefix}.{suffix}")

    text = _blank_spans(text, dotted_spans)

    for match in _IDENTIFIER_RE.finditer(text):
        token = match.group(0)
        if token.lower() in SQL_STOPWORDS:
            continue
        if token in known_aliases:
            continue
        if token in valid_tables or token in valid_columns:
            continue
        failures.append(token)

    return failures


def fetch_valid_names(cur):
    cur.execute("SELECT table_name FROM app.catalog_tables")
    valid_tables = {row[0] for row in cur.fetchall()}
    cur.execute("SELECT DISTINCT column_name FROM app.catalog_columns")
    valid_columns = {row[0] for row in cur.fetchall()}
    return valid_tables, valid_columns


def main():
    sql = generate_sql()
    print(f"Generated SQL:\n{sql}\n")

    failures = []
    if not sql.strip().upper().startswith("SELECT"):
        failures.append("SQL does not start with SELECT")

    conn = connect()
    try:
        with conn.cursor() as cur:
            valid_tables, valid_columns = fetch_valid_names(cur)
    finally:
        conn.close()

    unknown = check_references(sql, valid_tables, valid_columns)
    if unknown:
        failures.append(f"unknown table/column identifiers referenced: {unknown}")

    if failures:
        print("verify_generate_sql: FAILED")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)

    print("verify_generate_sql: PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
