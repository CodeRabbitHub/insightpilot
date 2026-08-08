import { useEffect, useState } from 'react'
import {
  deleteCard,
  errorMessage,
  fetchDashboard,
  renameCard,
  repositionCard,
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
  const [draggedCardId, setDraggedCardId] = useState<number | null>(null)

  useEffect(() => {
    let stale = false
    setLoading(true)
    setError(null)
    fetchDashboard(dashboardId)
      .then((data) => {
        if (!stale) setDashboard(data)
      })
      .catch((e: unknown) => {
        if (!stale) setError(errorMessage(e))
      })
      .finally(() => {
        if (!stale) setLoading(false)
      })
    return () => {
      stale = true
    }
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

  // Splice-out-then-splice-in at the target's index -- the standard list
  // drag-reorder semantic, so dropping on a card's slot inserts the
  // dragged card there and shifts that card (and everything after it)
  // down one. Every slot whose occupant changed gets PATCHed, not just
  // the dragged card, since a reorder shifts siblings too; any rejection
  // reverts the whole list back to its pre-drag arrangement.
  function handleDrop(targetCardId: number) {
    const draggedId = draggedCardId
    setDraggedCardId(null)
    if (!dashboard || draggedId === null || draggedId === targetCardId) return

    const previousCards = dashboard.cards
    const fromIndex = previousCards.findIndex((c) => c.id === draggedId)
    const toIndex = previousCards.findIndex((c) => c.id === targetCardId)
    if (fromIndex === -1 || toIndex === -1) return

    const reordered = [...previousCards]
    const [dragged] = reordered.splice(fromIndex, 1)
    reordered.splice(toIndex, 0, dragged)
    const renumbered = reordered.map((c, i) => ({ ...c, position: i }))

    setDashboard((prev) => (prev ? { ...prev, cards: renumbered } : prev))

    const changed = renumbered.filter((c, i) => previousCards[i]?.id !== c.id)
    Promise.all(changed.map((c) => repositionCard(c.id, c.position)))
      .then(() => setActionError(null))
      .catch((e: unknown) => {
        setActionError(errorMessage(e))
        setDashboard((prev) => (prev ? { ...prev, cards: previousCards } : prev))
      })
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
          <li
            key={card.id}
            draggable
            onDragStart={(e) => {
              setDraggedCardId(card.id)
              // Firefox refuses to start a native drag unless dragstart
              // calls setData; nothing reads it back since draggedCardId
              // already tracks the source card.
              e.dataTransfer.setData('text/plain', String(card.id))
            }}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              handleDrop(card.id)
            }}
          >
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
