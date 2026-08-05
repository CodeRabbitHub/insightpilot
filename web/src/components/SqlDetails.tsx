export function SqlDetails({
  sql,
  explanation,
}: {
  sql: string
  explanation: string
}) {
  return (
    <details className="mt-2 rounded border border-gray-200 p-2">
      <summary className="cursor-pointer text-sm font-medium text-gray-700">
        View SQL
      </summary>
      <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-sm">
        {sql}
      </pre>
      <p className="mt-2 text-sm text-gray-600">{explanation}</p>
    </details>
  )
}
