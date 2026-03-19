import { useEffect, useState } from 'react'
import { streamJob } from '../api'

export default function JobProgress({ jobId, onDone }) {
  const [events, setEvents] = useState([])
  const [pct, setPct] = useState(0)

  useEffect(() => {
    const es = streamJob(jobId, (event) => {
      setEvents(prev => {
        // Replace last downloading event to avoid spam
        if (event.step === 'downloading' && prev.length > 0 && prev[prev.length-1].step === 'downloading' && prev[prev.length-1].episode === event.episode) {
          return [...prev.slice(0, -1), event]
        }
        return [...prev, event]
      })
      if (event.pct >= 0) setPct(event.pct)
      if (event.step === 'done') onDone(event.digest_id)
      if (event.step === 'failed') onDone(null)
    })
    return () => es.close()
  }, [jobId])

  const stepLabel = {
    downloading: '⬇ Downloading',
    transcribing: '🎤 Transcribing',
    summarizing: '🤖 Summarizing',
    generating_script: '✍️ Writing script',
    tts: '🔊 Synthesizing audio',
    done: '✅ Done!',
    error: '❌ Error',
    failed: '❌ Failed',
  }

  return (
    <div className="bg-white rounded-xl border p-5">
      <h3 className="font-semibold mb-3">Generating Digest…</h3>
      <div className="w-full bg-gray-100 rounded-full h-2 mb-3">
        <div
          className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="space-y-1 max-h-48 overflow-y-auto text-sm">
        {events.map((e, i) => (
          <p key={i} className={e.step === 'error' || e.step === 'failed' ? 'text-red-600' : 'text-gray-600'}>
            <span className="font-medium">{stepLabel[e.step] || e.step}</span>
            {e.episode ? <span className="text-gray-500">: {e.episode}</span> : null}
            {e.message ? <span className="text-gray-400 text-xs"> — {e.message}</span> : null}
            {e.step !== 'downloading' && e.pct >= 0 ? <span className="text-gray-400 text-xs"> ({e.pct}%)</span> : null}
          </p>
        ))}
      </div>
    </div>
  )
}
