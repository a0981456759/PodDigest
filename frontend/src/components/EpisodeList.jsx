import { useEffect, useState } from 'react'
import { getShowEpisodes, getEpisodeTranscript, reprocessEpisode } from '../api'

function fmtDuration(sec) {
  if (!sec) return null
  if (sec >= 3600) return `${Math.floor(sec/3600)}h ${Math.floor((sec%3600)/60)}m`
  return `${Math.floor(sec/60)}m`
}

export default function EpisodeList({ show, selectedIds, onSelectionChange }) {
  const [episodes, setEpisodes] = useState([])
  const [loading, setLoading] = useState(true)
  const [expandedTranscript, setExpandedTranscript] = useState(null)
  const [transcripts, setTranscripts] = useState({})
  const [reprocessing, setReprocessing] = useState(null)

  useEffect(() => {
    setLoading(true)
    getShowEpisodes(show.id).then(eps => {
      setEpisodes(eps)
      setLoading(false)
    })
  }, [show.id])

  const toggle = (id) => {
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter(x => x !== id))
    } else {
      onSelectionChange([...selectedIds, id])
    }
  }

  const allSelected = episodes.length > 0 && episodes.every(e => selectedIds.includes(e.id))
  const toggleAll = () => {
    if (allSelected) onSelectionChange([])
    else onSelectionChange(episodes.map(e => e.id))
  }

  const toggleTranscript = async (ep) => {
    if (expandedTranscript === ep.id) {
      setExpandedTranscript(null)
      return
    }
    setExpandedTranscript(ep.id)
    if (!transcripts[ep.id]) {
      const data = await getEpisodeTranscript(ep.id)
      setTranscripts(prev => ({ ...prev, [ep.id]: data.transcript }))
    }
  }

  const handleReprocess = async (e, ep) => {
    e.stopPropagation()
    setReprocessing(ep.id)
    try {
      await reprocessEpisode(ep.id)
      // Refresh episode list
      const eps = await getShowEpisodes(show.id)
      setEpisodes(eps)
    } catch (err) {
      alert(err.message)
    } finally {
      setReprocessing(null)
    }
  }

  if (loading) return <div className="p-4 text-sm text-gray-400">Loading episodes…</div>
  if (!episodes.length) return <div className="p-4 text-sm text-gray-400">No episodes found.</div>

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-2 border-b bg-gray-50">
        <input type="checkbox" checked={allSelected} onChange={toggleAll} className="cursor-pointer" />
        <span className="text-xs text-gray-500">Select all ({episodes.length})</span>
        {selectedIds.length > 0 && (
          <span className="ml-auto text-xs text-indigo-600 font-medium">{selectedIds.length} selected</span>
        )}
      </div>
      <ul className="overflow-y-auto flex-1 divide-y">
        {episodes.map(ep => (
          <li key={ep.id} className="px-4 py-3 hover:bg-gray-50">
            <div className="flex items-start gap-3 cursor-pointer select-none" onClick={() => toggle(ep.id)}>
              <input
                type="checkbox"
                checked={selectedIds.includes(ep.id)}
                onChange={() => toggle(ep.id)}
                onClick={e => e.stopPropagation()}
                className="mt-1 cursor-pointer"
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{ep.title}</p>
                <div className="flex items-center flex-wrap gap-1.5 mt-0.5">
                  {ep.pub_date && <span className="text-xs text-gray-400">{ep.pub_date.slice(0, 10)}</span>}
                  {ep.duration_sec && <span className="text-xs text-gray-400">{fmtDuration(ep.duration_sec)}</span>}
                  {ep.has_transcript && <span className="text-xs bg-green-100 text-green-700 px-1 rounded">transcript</span>}
                  {ep.has_summary && <span className="text-xs bg-blue-100 text-blue-700 px-1 rounded">summarized</span>}
                  {ep.transcript_failed && <span className="text-xs bg-red-100 text-red-600 px-1 rounded">failed</span>}
                </div>
                <div className="flex gap-2 mt-1">
                  {ep.has_transcript && (
                    <button
                      onClick={e => { e.stopPropagation(); toggleTranscript(ep) }}
                      className="text-xs text-indigo-500 hover:underline"
                    >
                      {expandedTranscript === ep.id ? 'Hide transcript' : 'View transcript'}
                    </button>
                  )}
                  {(ep.transcript_failed || (!ep.has_transcript && !ep.has_summary)) && (
                    <button
                      onClick={e => handleReprocess(e, ep)}
                      disabled={reprocessing === ep.id}
                      className="text-xs text-orange-500 hover:underline disabled:opacity-50"
                    >
                      {reprocessing === ep.id ? 'Processing…' : 'Reprocess'}
                    </button>
                  )}
                </div>
              </div>
            </div>
            {expandedTranscript === ep.id && (
              <div className="mt-2 ml-7 p-2 bg-gray-50 rounded text-xs text-gray-600 max-h-48 overflow-y-auto whitespace-pre-wrap">
                {transcripts[ep.id] || 'Loading…'}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
