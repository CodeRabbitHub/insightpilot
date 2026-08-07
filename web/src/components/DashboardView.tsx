import { useEffect, useState } from 'react'
import {
  deleteCard,
  errorMessage,
  fetchDashboard,
  renameCard,
  runCard,
  type DashboardCardWithRows,
  type DashboardDetail,
} from '../api'
import { ChartView } from './ChartView'

export function DashboardView({ dashboardId }: { dashboardId: number }) {
  const [dashboard, setDashboard] = useState<DashboardDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // Separate from `error`: that state's `if (error) return <p>...</p>` guard
  // below would blank the whole card list on an action failure instead of
  // leaving cards in place, as each per-card action's brief has required.
  // Shared by delete/re-run/rename since each is a single button click at a
  // time -- no scenario needs their failures distinguished from each other.
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchDashboard(dashboardId)
      .then(setDashboard)
      .catch((e: unknown) => setError(errorMessage(e)))
      .finally(() => setLoading(false))
  }, [dashboardId])

  // Replaces exactly one card via `merge`, leaving every sibling untouched --
  // the shared shape behind both handleRerun's and handleRename's updates.
  function updateCard(
    cardId: number,
    merge: (card: DashboardCardWithRows) => DashboardCardWithRows,
  ) {
    setDashboard((prev) =>
      prev
        ? { ...prev, cards: prev.cards.map((c) => (c.id === cardId ? merge(c) : c)) }
        : prev,
    )
  }

  function handleDelete(cardId: number) {
    deleteCard(cardId)
      .then(() => {
        setActionError(null)
        setDashboard((prev) =>
          prev ? { ...prev, cards: prev.cards.filter((c) => c.id !== cardId) } : prev,
        )
      })
      .catch((e: unknown) => setActionError(errorMessage(e)))
  }

  function handleRerun(cardId: number) {
    runCard(cardId)
      .then((updated) => {
        setActionError(null)
        updateCard(cardId, () => updated)
      })
      .catch((e: unknown) => setActionError(errorMessage(e)))
  }

  function handleRename(cardId: number, currentTitle: string) {
    const input = window.prompt('New title', currentTitle)
    if (input === null) return
    const trimmed = input.trim()
    if (trimmed === '') return
    renameCard(cardId, trimmed)
      .then((updated) => {
        setActionError(null)
        updateCard(cardId, (c) => ({ ...c, title: updated.title }))
      })
      .catch((e: unknown) => setActionError(errorMessage(e)))
  }

  if (loading) return <p className="text-gray-500">Loading…</p>
  if (error) return <p className="text-red-600">Error: {error}</p>
  if (!dashboard) return null
  if (dashboard.cards.length === 0) {
    return <p className="text-gray-500">No pinned cards yet.</p>
  }

  return (
    <>
      {actionError && <p className="text-red-600">Error: {actionError}</p>}
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
                  onClick={() => handleRename(card.id, card.title)}
                  className="text-sm text-gray-700 hover:underline"
                >
                  Rename
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
