import { useState } from 'react'

export default function DigestHistory({ digests }) {
  const [expanded, setExpanded] = useState(null)
  const past = digests.slice(1)
  if (!past.length) return null

  return (
    <div className="bg-white rounded-xl border p-5">
      <h3 className="font-semibold mb-3">Past Digests</h3>
      <ul className="space-y-2">
        {past.map(d => (
          <li key={d.id} className="border rounded-lg overflow-hidden">
            <button
              onClick={() => setExpanded(expanded === d.id ? null : d.id)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 text-left"
            >
              <span className="text-sm font-medium">{d.title}</span>
              <span className="text-xs text-gray-400">
                {d.published_at ? new Date(d.published_at).toLocaleDateString() : ''}
                {' '}▶
              </span>
            </button>
            {expanded === d.id && d.audio_path && (
              <div className="px-4 pb-3">
                <audio controls src={`/api/digests/${d.id}/audio`} className="w-full" />
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
