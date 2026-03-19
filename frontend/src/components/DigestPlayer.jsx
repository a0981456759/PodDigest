import AudioPlayer from 'react-h5-audio-player'
import 'react-h5-audio-player/lib/styles.css'
import { useState } from 'react'
import { resynthesizeDigest } from '../api'

export default function DigestPlayer({ digests, prefs, onJobStart }) {
  const [copied, setCopied] = useState(false)
  const [showScript, setShowScript] = useState(false)
  const [editingScript, setEditingScript] = useState(false)
  const [scriptDraft, setScriptDraft] = useState('')
  const [resynthLoading, setResynthLoading] = useState(false)
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

  const handleEditScript = () => {
    setScriptDraft(latest.script)
    setEditingScript(true)
    setShowScript(true)
  }

  const handleResynthesize = async () => {
    setResynthLoading(true)
    try {
      const { job_id } = await resynthesizeDigest(latest.id, editingScript ? scriptDraft : null)
      setEditingScript(false)
      if (onJobStart) onJobStart(job_id)
    } catch (e) {
      alert(e.message)
    } finally {
      setResynthLoading(false)
    }
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
            {latest.cost_usd ? ` · ~$${latest.cost_usd.toFixed(3)}` : ''}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setShowScript(s => !s); setEditingScript(false) }}
            className="text-xs px-2 py-1 border rounded hover:bg-gray-50"
          >
            {showScript ? 'Hide script' : 'View script'}
          </button>
          <button
            onClick={handleEditScript}
            className="text-xs px-2 py-1 border rounded hover:bg-gray-50"
          >
            Edit & Resynthesize
          </button>
        </div>
      </div>

      {latest.audio_path && (
        <AudioPlayer src={audioUrl} showJumpControls={false} className="rounded-lg" />
      )}

      {showScript && (
        <div className="mt-4">
          {editingScript ? (
            <div>
              <textarea
                value={scriptDraft}
                onChange={e => setScriptDraft(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm h-64 resize-y font-mono"
              />
              <div className="flex gap-2 mt-2">
                <button
                  onClick={handleResynthesize}
                  disabled={resynthLoading}
                  className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm disabled:opacity-50"
                >
                  {resynthLoading ? 'Starting…' : '▶ Resynthesize Audio'}
                </button>
                <button
                  onClick={() => setEditingScript(false)}
                  className="px-3 py-1.5 border rounded text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-gray-50 rounded p-3 text-sm text-gray-700 max-h-64 overflow-y-auto whitespace-pre-wrap">
              {latest.script}
            </div>
          )}
        </div>
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
