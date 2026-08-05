import ReactECharts from 'echarts-for-react'

const SERIES_COLOR = '#2a78d6'
const GRIDLINE_COLOR = '#e1e0d9'
const AXIS_LABEL_COLOR = '#898781'
const PRIMARY_INK = '#0b0b0b'

function resolveField(
  chartSpec: Record<string, unknown>,
  keys: string[],
): string | null {
  for (const key of keys) {
    const value = chartSpec[key]
    if (typeof value === 'string' && value.trim() !== '') return value
  }
  return null
}

function toFiniteNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return null
}

export function ChartView({
  chartSpec,
  rows,
}: {
  chartSpec: Record<string, unknown>
  rows: Record<string, unknown>[]
}) {
  const chartType = resolveField(chartSpec, ['chart_type', 'type'])
  if (chartType !== 'bar') return null
  if (rows.length === 0) return null

  const xField = resolveField(chartSpec, ['x', 'x_field'])
  const yField = resolveField(chartSpec, ['y', 'y_field'])
  if (!xField || !yField) return null
  if (!(xField in rows[0]) || !(yField in rows[0])) return null

  const categories: string[] = []
  const values: number[] = []
  for (const row of rows) {
    const value = toFiniteNumber(row[yField])
    if (value === null) return null
    categories.push(String(row[xField]))
    values.push(value)
  }

  const title =
    typeof chartSpec.title === 'string' && chartSpec.title.trim() !== ''
      ? chartSpec.title
      : `${yField} by ${xField}`

  const option = {
    color: [SERIES_COLOR],
    title: {
      text: title,
      left: 'center',
      textStyle: { fontSize: 14, fontWeight: 600, color: PRIMARY_INK },
    },
    tooltip: { trigger: 'axis' },
    grid: { top: 48, right: 16, bottom: 40, left: 48, containLabel: true },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: { lineStyle: { color: GRIDLINE_COLOR } },
      axisLabel: { color: AXIS_LABEL_COLOR },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: GRIDLINE_COLOR } },
      axisLabel: { color: AXIS_LABEL_COLOR },
    },
    series: [
      {
        type: 'bar',
        data: values,
        barMaxWidth: 24,
        itemStyle: { color: SERIES_COLOR, borderRadius: [4, 4, 0, 0] },
      },
    ],
  }

  return (
    <div className="mt-2 rounded border border-gray-200 p-2">
      <ReactECharts option={option} style={{ height: 260 }} />
    </div>
  )
}
