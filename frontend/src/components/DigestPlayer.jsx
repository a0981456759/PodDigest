import AudioPlayer from 'react-h5-audio-player'
import 'react-h5-audio-player/lib/styles.css'
import { useState } from 'react'

export default function DigestPlayer({ digests, prefs }) {
  const [copied, setCopied] = useState(false)
  const latest = digests[0]

  const feedUrl = prefs?.feed_token
    ? `${window.location.origin}/api/feed/${prefs.feed_token}`
    : null

  const handleCopy = () => {
    if (!feedUrl) return
    navigator.clipboard.writeText(feedUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!latest) {
    return (
      <div className="bg-white rounded-xl border p-6 text-center text-gray-400">
        No digests yet. Add some shows and click &quot;Generate Digest&quot;.
      </div>
    )
  }

  const audioUrl = `/api/digests/${latest.id}/audio`

  return (
    <div className="bg-white rounded-xl border p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h2 className="font-semibold text-lg">{latest.title}</h2>
          <p className="text-sm text-gray-500">
            {latest.published_at ? new Date(latest.published_at).toLocaleDateString() : ''}
            {latest.duration_sec ? ` · ${Math.floor(latest.duration_sec / 60)}m ${latest.duration_sec % 60}s` : ''}
          </p>
        </div>
      </div>

      {latest.audio_path && (
        <AudioPlayer src={audioUrl} showJumpControls={false} className="rounded-lg" />
      )}

      {feedUrl && (
        <div className="mt-4 flex items-center gap-2">
          <input
            readOnly value={feedUrl}
            className="flex-1 border rounded px-3 py-1.5 text-xs text-gray-600 bg-gray-50"
          />
          <button onClick={handleCopy}
            className="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded border">
            {copied ? '✓ Copied' : '📋 Copy RSS'}
          </button>
        </div>
      )}
    </div>
  )
}
