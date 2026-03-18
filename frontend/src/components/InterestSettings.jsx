import { useState } from 'react'
import { updatePreferences } from '../api'

const PRESET_TAGS = ['AI', 'Technology', 'Startups', 'Investing', 'Science',
  'Politics', 'History', 'Health', 'Business', 'Design', 'Taiwan', 'China']

export default function InterestSettings({ prefs, onPrefsChange }) {
  const [tags, setTags] = useState(prefs.topic_tags || [])
  const [desc, setDesc] = useState(prefs.interest_description || '')
  const [saving, setSaving] = useState(false)

  const toggleTag = (tag) => {
    setTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag])
  }

  const save = async () => {
    setSaving(true)
    const updated = await updatePreferences({ topic_tags: tags, interest_description: desc })
    onPrefsChange(updated)
    setSaving(false)
  }

  return (
    <div className="p-4 border-t">
      <h2 className="font-semibold text-sm text-gray-500 uppercase tracking-wide mb-3">Interests</h2>
      <div className="flex flex-wrap gap-1 mb-3">
        {PRESET_TAGS.map(tag => (
          <button key={tag} onClick={() => toggleTag(tag)}
            className={`px-2 py-0.5 rounded-full text-xs border ${
              tags.includes(tag) ? 'bg-indigo-600 text-white border-indigo-600' : 'text-gray-600 border-gray-300'
            }`}>
            {tag}
          </button>
        ))}
      </div>
      <textarea
        value={desc}
        onChange={e => setDesc(e.target.value)}
        placeholder="Describe your interests in more detail..."
        className="w-full border rounded px-3 py-2 text-sm resize-none h-20 mb-2"
      />
      <button onClick={save} disabled={saving}
        className="w-full py-1.5 bg-indigo-600 text-white rounded text-sm disabled:opacity-50">
        {saving ? 'Saving...' : 'Save Interests'}
      </button>
    </div>
  )
}
