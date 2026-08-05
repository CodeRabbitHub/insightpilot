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
