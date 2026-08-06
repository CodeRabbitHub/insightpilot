export function FollowUpChips({
  followUps,
  onSelect,
}: {
  followUps: string[]
  onSelect: (text: string) => void
}) {
  if (followUps.length === 0) return null
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {followUps.map((text, i) => (
        <button
          key={i}
          type="button"
          onClick={() => onSelect(text)}
          className="rounded-full border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-50"
        >
          {text}
        </button>
      ))}
    </div>
  )
}
