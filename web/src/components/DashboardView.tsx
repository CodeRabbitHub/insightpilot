import { useEffect, useState } from 'react'
import { errorMessage, fetchDashboard, type DashboardDetail } from '../api'
import { ChartView } from './ChartView'

export function DashboardView({ dashboardId }: { dashboardId: number }) {
  const [dashboard, setDashboard] = useState<DashboardDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchDashboard(dashboardId)
      .then(setDashboard)
      .catch((e: unknown) => setError(errorMessage(e)))
      .finally(() => setLoading(false))
  }, [dashboardId])

  if (loading) return <p className="text-gray-500">Loading…</p>
  if (error) return <p className="text-red-600">Error: {error}</p>
  if (!dashboard) return null
  if (dashboard.cards.length === 0) {
    return <p className="text-gray-500">No pinned cards yet.</p>
  }

  return (
    <ul className="space-y-6">
      {dashboard.cards.map((card) => (
        <li key={card.id}>
          <h3 className="text-base font-medium">{card.title}</h3>
          <ChartView chartSpec={card.chart_spec_json} rows={card.rows} />
        </li>
      ))}
    </ul>
  )
}
