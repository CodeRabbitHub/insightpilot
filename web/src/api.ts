const API_BASE = "http://localhost:8000"

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

export interface ConversationSummary {
  id: number
  title: string | null
  created_at: string
}

export interface MessageDetail {
  id: number
  role: string
  content_json: Record<string, unknown>
  created_at: string
}

export interface ConversationDetail {
  id: number
  title: string | null
  created_at: string
  messages: MessageDetail[]
}

export async function fetchConversations(): Promise<ConversationSummary[]> {
  const response = await fetch(`${API_BASE}/api/conversations`)
  if (!response.ok) {
    throw new Error(`GET /api/conversations failed: ${response.status}`)
  }
  return response.json()
}

export async function fetchConversation(id: number): Promise<ConversationDetail> {
  const response = await fetch(`${API_BASE}/api/conversations/${id}`)
  if (!response.ok) {
    throw new Error(`GET /api/conversations/${id} failed: ${response.status}`)
  }
  return response.json()
}

export interface DashboardCardWithRows {
  id: number
  dashboard_id: number
  title: string
  question_text: string
  sql_text: string
  chart_spec_json: Record<string, unknown>
  position: number
  created_at: string
  rows: Record<string, unknown>[]
}

export interface DashboardDetail {
  id: number
  name: string
  created_at: string
  cards: DashboardCardWithRows[]
}

export async function fetchDashboard(id: number): Promise<DashboardDetail> {
  const response = await fetch(`${API_BASE}/api/dashboards/${id}`)
  if (!response.ok) {
    throw new Error(`GET /api/dashboards/${id} failed: ${response.status}`)
  }
  return response.json()
}

export async function deleteCard(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/api/cards/${id}`, { method: 'DELETE' })
  if (!response.ok) {
    throw new Error(`DELETE /api/cards/${id} failed: ${response.status}`)
  }
}

export interface Analysis {
  summary: string
  explanation: string
  chart_spec: Record<string, unknown>
  follow_ups: string[]
}

export interface ConversationMessageResult {
  conversation_id: number
  message_id: number
  sql: string
  rows: Record<string, unknown>[]
  analysis: Analysis
}

export interface AssistantContent {
  rows: Record<string, unknown>[]
  chartSpec: Record<string, unknown>
  sql: string
  explanation: string
  followUps: string[]
}

// content_json holds {question} for user messages and {sql, rows, analysis}
// for assistant ones, so MessageDetail can't type it narrower -- this is the
// one runtime check that a given message has the shape any per-message
// assistant component needs, before each does its own further resolution.
export function asAssistantContent(
  contentJson: Record<string, unknown>,
): AssistantContent | null {
  const rows = contentJson.rows
  const analysis = contentJson.analysis
  const sql = contentJson.sql
  if (!Array.isArray(rows)) return null
  if (typeof analysis !== 'object' || analysis === null) return null
  if (typeof sql !== 'string') return null
  const chartSpec = (analysis as Record<string, unknown>).chart_spec
  if (typeof chartSpec !== 'object' || chartSpec === null) return null
  const explanation = (analysis as Record<string, unknown>).explanation
  if (typeof explanation !== 'string') return null
  const followUps = (analysis as Record<string, unknown>).follow_ups
  if (!Array.isArray(followUps)) return null
  return {
    rows: rows as Record<string, unknown>[],
    chartSpec: chartSpec as Record<string, unknown>,
    sql,
    explanation,
    followUps: followUps as string[],
  }
}

export async function postConversationMessage(
  conversationId: number,
  question: string,
): Promise<ConversationMessageResult> {
  const response = await fetch(
    `${API_BASE}/api/conversations/${conversationId}/messages`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    },
  )
  if (!response.ok) {
    throw new Error(
      `POST /api/conversations/${conversationId}/messages failed: ${response.status}`,
    )
  }
  if (!response.body) {
    throw new Error('response body is empty')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  // The endpoint always emits exactly one SSE event then closes the stream
  // (app/main.py _conversation_message_stream_events), so draining to
  // completion before parsing is simpler than incremental frame detection
  // and cannot hang, given that contract.
  while (true) {
    const { done, value } = await reader.read()
    if (value) buffer += decoder.decode(value, { stream: true })
    if (done) break
  }
  buffer += decoder.decode()

  const lines = buffer.split('\n')
  const eventLine = lines.find((line) => line.startsWith('event: '))
  const dataLine = lines.find((line) => line.startsWith('data: '))
  if (!eventLine || !dataLine) {
    throw new Error('malformed SSE response from message stream')
  }
  const data = JSON.parse(dataLine.slice('data: '.length))
  if (eventLine === 'event: error') {
    const detail = typeof data.detail === 'string' ? data.detail : 'unknown error'
    throw new Error(detail)
  }
  return data as ConversationMessageResult
}
