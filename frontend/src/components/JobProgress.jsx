import { useEffect, useState } from 'react'
import { streamJob } from '../api'

export default function JobProgress({ jobId, onDone }) {
  const [events, setEvents] = useState([])
  const [pct, setPct] = useState(0)

  useEffect(() => {
    const es = streamJob(jobId, (event) => {
      setEvents(prev => [...prev, event])
      if (event.pct >= 0) setPct(event.pct)
      if (event.step === 'done') onDone(event.digest_id)
    })
    return () => es.close()
  }, [jobId])

  const stepLabel = {
    transcribing: 'Transcribing',
    summarizing: 'Summarizing',
    generating_script: 'Writing digest script',
    tts: 'Synthesizing audio',
    done: 'Done!',
    error: 'Error',
  }

  const latest = events[events.length - 1]

  return (
    <div className="bg-white rounded-xl border p-5">
      <h3 className="font-semibold mb-3">Generating Digest...</h3>
      <div className="w-full bg-gray-100 rounded-full h-2 mb-3">
        <div
          className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="space-y-1 max-h-48 overflow-y-auto">
        {events.map((e, i) => (
          <p key={i} className={`text-sm ${e.step === 'error' ? 'text-red-600' : 'text-gray-600'}`}>
            {stepLabel[e.step] || e.step}
            {e.episode ? `: ${e.episode}` : ''}
            {e.pct >= 0 ? ` (${e.pct}%)` : ''}
          </p>
        ))}
      </div>
      {latest && <p className="sr-only">{latest.step}</p>}
    </div>
  )
}
