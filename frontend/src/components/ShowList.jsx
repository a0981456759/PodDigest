import { useState } from 'react'
import AddShowModal from './AddShowModal'
import { deleteShow, getShows } from '../api'

export default function ShowList({ shows, onShowsChange }) {
  const [showModal, setShowModal] = useState(false)

  const handleDelete = async (id) => {
    await deleteShow(id)
    onShowsChange(shows.filter(s => s.id !== id))
  }

  const handleAdded = (newShows) => {
    if (newShows === null) {
      // OPML import: refresh full list
      getShows().then(onShowsChange)
    } else {
      onShowsChange([...shows, ...newShows])
    }
    setShowModal(false)
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold text-sm text-gray-500 uppercase tracking-wide">Shows</h2>
      </div>
      <ul className="space-y-1 mb-3">
        {shows.map(show => (
          <li key={show.id} className="flex items-center gap-2 group">
            {show.artwork_url
              ? <img src={show.artwork_url} className="w-7 h-7 rounded" alt="" />
              : <span className="w-7 h-7 bg-indigo-100 rounded flex items-center justify-center text-xs">🎵</span>
            }
            <span className="flex-1 text-sm truncate">{show.title}</span>
            <button
              onClick={() => handleDelete(show.id)}
              className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 text-xs"
            >×</button>
          </li>
        ))}
      </ul>
      <div className="flex flex-col gap-1">
        <button
          onClick={() => setShowModal(true)}
          className="w-full text-left text-sm text-indigo-600 hover:text-indigo-800 py-1"
        >+ Add Show</button>
      </div>
      {showModal && <AddShowModal onClose={() => setShowModal(false)} onAdded={handleAdded} />}
    </div>
  )
}
