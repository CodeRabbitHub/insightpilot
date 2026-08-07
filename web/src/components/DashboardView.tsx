import { useEffect, useState } from 'react'
import { deleteCard, errorMessage, fetchDashboard, runCard, type DashboardDetail } from '../api'
import { ChartView } from './ChartView'

export function DashboardView({ dashboardId }: { dashboardId: number }) {
  const [dashboard, setDashboard] = useState<DashboardDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // Separate from `error`: that state's `if (error) return <p>...</p>` guard
  // below would blank the whole card list on a delete failure instead of
  // leaving cards in place, as the brief requires.
  const [deleteError, setDeleteError] = useState<string | null>(null)
  // Separate from both `error` and `deleteError` for the same reason.
  const [rerunError, setRerunError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchDashboard(dashboardId)
      .then(setDashboard)
      .catch((e: unknown) => setError(errorMessage(e)))
      .finally(() => setLoading(false))
  }, [dashboardId])

  function handleDelete(cardId: number) {
    deleteCard(cardId)
      .then(() => {
        setDeleteError(null)
        setDashboard((prev) =>
          prev ? { ...prev, cards: prev.cards.filter((c) => c.id !== cardId) } : prev,
        )
      })
      .catch((e: unknown) => setDeleteError(errorMessage(e)))
  }

  function handleRerun(cardId: number) {
    runCard(cardId)
      .then((updated) => {
        setRerunError(null)
        setDashboard((prev) =>
          prev
            ? { ...prev, cards: prev.cards.map((c) => (c.id === cardId ? updated : c)) }
            : prev,
        )
      })
      .catch((e: unknown) => setRerunError(errorMessage(e)))
  }

  if (loading) return <p className="text-gray-500">Loading…</p>
  if (error) return <p className="text-red-600">Error: {error}</p>
  if (!dashboard) return null
  if (dashboard.cards.length === 0) {
    return <p className="text-gray-500">No pinned cards yet.</p>
  }

  return (
    <>
      {deleteError && <p className="text-red-600">Error: {deleteError}</p>}
      {rerunError && <p className="text-red-600">Error: {rerunError}</p>}
      <ul className="space-y-6">
        {dashboard.cards.map((card) => (
          <li key={card.id}>
            <div className="flex items-center justify-between">
              <h3 className="text-base font-medium">{card.title}</h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleRerun(card.id)}
                  className="text-sm text-blue-600 hover:underline"
                >
                  Re-run
                </button>
                <button
                  onClick={() => handleDelete(card.id)}
                  className="text-sm text-red-600 hover:underline"
                >
                  Delete
                </button>
              </div>
            </div>
            <ChartView chartSpec={card.chart_spec_json} rows={card.rows} />
          </li>
        ))}
      </ul>
    </>
  )
}
