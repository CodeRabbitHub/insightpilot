import { useEffect, useState } from 'react'
import {
  fetchConversation,
  fetchConversations,
  type ConversationDetail,
  type ConversationSummary,
} from './api'

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString()
}

function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
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
}: {
  conversation: ConversationDetail
  onBack: () => void
}) {
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
          </li>
        ))}
      </ul>
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
  }, [selectedId])

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-4 text-2xl font-bold">InsightPilot conversations</h1>
      {loading && <p className="text-gray-500">Loading…</p>}
      {error && <p className="text-red-600">Error: {error}</p>}
      {!loading && !error && selectedId === null && (
        <ConversationList
          conversations={conversations}
          onSelect={setSelectedId}
        />
      )}
      {!loading && !error && selectedId !== null && selectedConversation && (
        <ConversationDetailView
          conversation={selectedConversation}
          onBack={() => setSelectedId(null)}
        />
      )}
    </div>
  )
}

export default App
