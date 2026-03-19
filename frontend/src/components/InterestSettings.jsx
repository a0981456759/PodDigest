import { useState } from 'react'
import { updatePreferences } from '../api'

const PRESET_TAGS = ['AI', 'Technology', 'Startups', 'Investing', 'Science',
  'Politics', 'History', 'Health', 'Business', 'Design', 'Taiwan', 'China']

export default function InterestSettings({ prefs, onPrefsChange }) {
  const [tags, setTags] = useState(prefs.topic_tags || [])
  const [desc, setDesc] = useState(prefs.interest_description || '')
  const [customInput, setCustomInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const toggleTag = (tag) => {
    setTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag])
  }

  const addCustomTag = () => {
    const t = customInput.trim()
    if (t && !tags.includes(t)) {
      setTags(prev => [...prev, t])
    }
    setCustomInput('')
  }

  const removeTag = (tag) => {
    setTags(prev => prev.filter(t => t !== tag))
  }

  const save = async () => {
    setSaving(true)
    const updated = await updatePreferences({ topic_tags: tags, interest_description: desc })
    onPrefsChange(updated)
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  // Tags not in preset (custom ones)
  const customTags = tags.filter(t => !PRESET_TAGS.includes(t))

  return (
    <div className="p-4 border-t">
      <h2 className="font-semibold text-sm text-gray-500 uppercase tracking-wide mb-3">Interests</h2>

      {/* Preset tags */}
      <p className="text-xs text-gray-400 mb-1">Topics</p>
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

      {/* Custom tags */}
      <p className="text-xs text-gray-400 mb-1">Custom tags</p>
      <div className="border rounded px-2 py-2 mb-3 min-h-[40px]">
        <div className="flex flex-wrap gap-1 mb-1">
          {customTags.map(tag => (
            <span key={tag} className="flex items-center gap-1 px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full text-xs">
              {tag}
              <button onClick={() => removeTag(tag)} className="hover:text-red-500 leading-none">×</button>
            </span>
          ))}
        </div>
        <div className="flex gap-1">
          <input
            value={customInput}
            onChange={e => setCustomInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addCustomTag()}
            placeholder="Add tag, press Enter"
            className="flex-1 text-xs outline-none bg-transparent"
          />
          {customInput && (
            <button onClick={addCustomTag} className="text-xs text-indigo-600 hover:underline">Add</button>
          )}
        </div>
      </div>

      {/* Description */}
      <p className="text-xs text-gray-400 mb-1">Description</p>
      <div className="border rounded mb-3">
        <textarea
          value={desc}
          onChange={e => setDesc(e.target.value)}
          placeholder="Describe your interests in more detail..."
          className="w-full px-3 py-2 text-sm resize-none h-20 outline-none rounded bg-transparent"
        />
      </div>

      <button onClick={save} disabled={saving}
        className="w-full py-1.5 bg-indigo-600 text-white rounded text-sm disabled:opacity-50">
        {saving ? 'Saving...' : saved ? '✓ Saved' : 'Save Interests'}
      </button>
    </div>
  )
}
