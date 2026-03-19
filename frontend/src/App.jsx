import { useState, useEffect } from 'react'
import ShowList from './components/ShowList'
import EpisodeList from './components/EpisodeList'
import DigestPlayer from './components/DigestPlayer'
import DigestHistory from './components/DigestHistory'
import JobProgress from './components/JobProgress'
import InterestSettings from './components/InterestSettings'
import ScheduleSettings from './components/ScheduleSettings'
import { getShows, getDigests, getPreferences, triggerDigest } from './api'

export default function App() {
  const [shows, setShows] = useState([])
  const [digests, setDigests] = useState([])
  const [prefs, setPrefs] = useState(null)
  const [activeJob, setActiveJob] = useState(null)
  const [error, setError] = useState(null)
  const [selectedShow, setSelectedShow] = useState(null)
  const [selectedEpisodeIds, setSelectedEpisodeIds] = useState([])

  useEffect(() => {
    getShows().then(setShows)
    getDigests().then(setDigests)
    getPreferences().then(setPrefs)
  }, [])

  const handleSelectShow = (show) => {
    if (selectedShow?.id === show.id) {
      setSelectedShow(null)
    } else {
      setSelectedShow(show)
    }
  }

  const handleTrigger = async () => {
    try {
      const ids = selectedEpisodeIds.length > 0 ? selectedEpisodeIds : null
      const { job_id } = await triggerDigest(ids)
      setActiveJob(job_id)
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }

  const handleJobDone = () => {
    setActiveJob(null)
    getDigests().then(setDigests)
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50 text-gray-900">
      {/* Top bar */}
      <header className="flex items-center justify-between px-6 py-3 bg-white border-b shadow-sm">
        <h1 className="text-xl font-bold">🎙 PodDigest</h1>
        <div className="flex gap-3 items-center">
          {prefs && (
            <span className="text-sm text-gray-500">
              Language: {prefs.output_language.toUpperCase()}
            </span>
          )}
          {selectedEpisodeIds.length > 0 && (
            <span className="text-sm text-indigo-600 flex items-center gap-1">
              {selectedEpisodeIds.length} 集已選
              <button onClick={() => setSelectedEpisodeIds([])} className="text-gray-400 hover:text-gray-600 ml-1">×</button>
            </span>
          )}
          <button
            onClick={handleTrigger}
            disabled={!!activeJob}
            className="px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {activeJob ? 'Processing...' : selectedEpisodeIds.length > 0 ? '▶ Generate from Selected' : '▶ Generate Digest'}
          </button>
        </div>
      </header>

      {error && (
        <div className="mx-6 mt-3 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error} <button onClick={() => setError(null)} className="ml-2 font-bold">×</button>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-white border-r flex flex-col overflow-y-auto">
          <ShowList
            shows={shows}
            onShowsChange={setShows}
            selectedShow={selectedShow}
            onSelectShow={handleSelectShow}
          />
          {prefs && (
            <>
              <InterestSettings prefs={prefs} onPrefsChange={setPrefs} />
              <ScheduleSettings prefs={prefs} onPrefsChange={setPrefs} />
            </>
          )}
        </aside>

        {/* Episode panel */}
        {selectedShow && (
          <div className="w-80 bg-white border-r flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b">
              <h2 className="font-semibold text-sm truncate">{selectedShow.title}</h2>
              <p className="text-xs text-gray-400 mt-0.5">Click episodes to select for digest</p>
            </div>
            <EpisodeList
              show={selectedShow}
              selectedIds={selectedEpisodeIds}
              onSelectionChange={setSelectedEpisodeIds}
            />
          </div>
        )}

        {/* Main panel */}
        <main className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
          <DigestPlayer digests={digests} prefs={prefs} onJobStart={setActiveJob} />
          {activeJob && <JobProgress jobId={activeJob} onDone={handleJobDone} />}
          <DigestHistory digests={digests} />
        </main>
      </div>
    </div>
  )
}
