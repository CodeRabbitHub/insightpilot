const API_BASE = "http://localhost:8000"

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

export interface ConversationMessageResult {
  conversation_id: number
  message_id: number
  sql: string
  rows: Record<string, unknown>[]
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
