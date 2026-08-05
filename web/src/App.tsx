import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  asAssistantContent,
  fetchConversation,
  fetchConversations,
  postConversationMessage,
  type ConversationDetail,
  type ConversationSummary,
  type MessageDetail,
} from './api'
import { ChartView } from './components/ChartView'

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString()
}

function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

function AssistantChart({ message }: { message: MessageDetail }) {
  const content = asAssistantContent(message.content_json)
  if (!content) return null
  return <ChartView chartSpec={content.chartSpec} rows={content.rows} />
}

function ConversationList({
  conversations,
  onSelect,
}: {
  conversations: ConversationSummary[]
  onSelect: (id: number) => void
}) {
  if (conversations.length === 0) {
    return <p className="text-gray-500">No conversations yet.</p>
  }
  return (
    <ul className="divide-y divide-gray-200">
      {conversations.map((c) => (
        <li key={c.id}>
          <button
            type="button"
            onClick={() => onSelect(c.id)}
            className="w-full py-3 px-2 text-left hover:bg-gray-50"
          >
            <div className="font-medium">{c.title ?? 'Untitled'}</div>
            <div className="text-sm text-gray-500">
              #{c.id} · {formatTimestamp(c.created_at)}
            </div>
          </button>
        </li>
      ))}
    </ul>
  )
}

function ConversationDetailView({
  conversation,
  onBack,
  onMessageSent,
}: {
  conversation: ConversationDetail
  onBack: () => void
  onMessageSent: () => void
}) {
  const [question, setQuestion] = useState('')
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const trimmed = question.trim()
    if (trimmed === '' || sending) return
    setSending(true)
    setSendError(null)
    postConversationMessage(conversation.id, trimmed)
      .then(() => {
        setQuestion('')
        onMessageSent()
      })
      .catch((err: unknown) => setSendError(errorMessage(err)))
      .finally(() => setSending(false))
  }

  return (
    <div>
      <button
        type="button"
        onClick={onBack}
        className="mb-4 text-sm text-blue-600 hover:underline"
      >
        ← Back
      </button>
      <h2 className="text-lg font-semibold">
        {conversation.title ?? 'Untitled'}
      </h2>
      <p className="mb-4 text-sm text-gray-500">
        #{conversation.id} · {formatTimestamp(conversation.created_at)}
      </p>
      <ul className="space-y-3">
        {conversation.messages.map((m) => (
          <li key={m.id} className="rounded border border-gray-200 p-3">
            <div className="mb-1 text-xs font-semibold uppercase text-gray-500">
              {m.role}
            </div>
            <pre className="overflow-x-auto whitespace-pre-wrap text-sm">
              {JSON.stringify(m.content_json, null, 2)}
            </pre>
            {m.role === 'assistant' && <AssistantChart message={m} />}
          </li>
        ))}
      </ul>
      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={sending}
          placeholder="Ask a question…"
          className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={sending || question.trim() === ''}
          className="rounded bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {sending ? 'Sending…' : 'Send'}
        </button>
      </form>
      {sendError && (
        <p className="mt-2 text-sm text-red-600">Error: {sendError}</p>
      )}
    </div>
  )
}

function App() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selectedConversation, setSelectedConversation] =
    useState<ConversationDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchConversations()
      .then(setConversations)
      .catch((e: unknown) => setError(errorMessage(e)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (selectedId === null) {
      setSelectedConversation(null)
      return
    }
    let stale = false
    setLoading(true)
    setError(null)
    fetchConversation(selectedId)
      .then((detail) => {
        if (!stale) setSelectedConversation(detail)
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
  }, [selectedId, refreshKey])

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-4 text-2xl font-bold">InsightPilot conversations</h1>
      {loading && !selectedConversation && (
        <p className="text-gray-500">Loading…</p>
      )}
      {error && <p className="text-red-600">Error: {error}</p>}
      {!loading && !error && selectedId === null && (
        <ConversationList
          conversations={conversations}
          onSelect={setSelectedId}
        />
      )}
      {selectedId !== null && selectedConversation && (
        <ConversationDetailView
          conversation={selectedConversation}
          onBack={() => setSelectedId(null)}
          onMessageSent={() => setRefreshKey((k) => k + 1)}
        />
      )}
    </div>
  )
}

export default App
