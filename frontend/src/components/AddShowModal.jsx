import { useState } from 'react'
import { searchShows, addShow, importOpml } from '../api'

export default function AddShowModal({ onClose, onAdded }) {
  const [tab, setTab] = useState('search')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [rssUrl, setRssUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await searchShows(query)
      setResults(data)
    } catch (e) {
      setError('Search failed')
    } finally {
      setLoading(false)
    }
  }

  const handleAddFromSearch = async (result) => {
    setLoading(true)
    try {
      const show = await addShow(result.rss_url)
      onAdded([show])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAddByUrl = async () => {
    if (!rssUrl.trim()) return
    setLoading(true)
    setError(null)
    try {
      const show = await addShow(rssUrl.trim())
      onAdded([show])
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  const handleOpml = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      await importOpml(file)
      // Refresh full show list by reloading — parent handles via onAdded with empty array trigger
      onAdded([])
      onClose()
    } catch (e) {
      setError('Import failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold">Add Podcast</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">×</button>
        </div>

        <div className="flex border-b">
          {['search', 'url', 'opml'].map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`flex-1 py-2 text-sm font-medium capitalize ${tab === t ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500'}`}>
              {t === 'opml' ? 'Import OPML' : t === 'url' ? 'RSS URL' : 'Search'}
            </button>
          ))}
        </div>

        <div className="p-4">
          {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

          {tab === 'search' && (
            <div>
              <div className="flex gap-2 mb-3">
                <input value={query} onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSearch()}
                  placeholder="Search podcasts..." className="flex-1 border rounded px-3 py-2 text-sm" />
                <button onClick={handleSearch} disabled={loading}
                  className="px-3 py-2 bg-indigo-600 text-white rounded text-sm disabled:opacity-50">
                  {loading ? '...' : 'Search'}
                </button>
              </div>
              <ul className="space-y-2 max-h-64 overflow-y-auto">
                {results.map((r, i) => (
                  <li key={i} className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer"
                    onClick={() => handleAddFromSearch(r)}>
                    {r.artwork_url && <img src={r.artwork_url} className="w-10 h-10 rounded" alt="" />}
                    <div>
                      <p className="text-sm font-medium">{r.title}</p>
                      <p className="text-xs text-gray-500">{r.author}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {tab === 'url' && (
            <div className="flex gap-2">
              <input value={rssUrl} onChange={e => setRssUrl(e.target.value)}
                placeholder="https://example.com/feed.xml"
                className="flex-1 border rounded px-3 py-2 text-sm" />
              <button onClick={handleAddByUrl} disabled={loading}
                className="px-3 py-2 bg-indigo-600 text-white rounded text-sm disabled:opacity-50">
                {loading ? '...' : 'Add'}
              </button>
            </div>
          )}

          {tab === 'opml' && (
            <div className="text-center py-4">
              <p className="text-sm text-gray-600 mb-3">
                Export OPML from Apple Podcasts: Library → ··· → Export OPML
              </p>
              <label className="px-4 py-2 bg-indigo-600 text-white rounded cursor-pointer text-sm">
                Choose OPML file
                <input type="file" accept=".opml,.xml" className="hidden" onChange={handleOpml} />
              </label>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
