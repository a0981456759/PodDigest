import { useState } from 'react'
import { updatePreferences } from '../api'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function ScheduleSettings({ prefs, onPrefsChange }) {
  const [type, setType] = useState(prefs.schedule_type || 'weekly')
  const [day, setDay] = useState(prefs.schedule_day ?? 0)
  const [hour, setHour] = useState(prefs.schedule_hour ?? 8)
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    const updated = await updatePreferences({ schedule_type: type, schedule_day: day, schedule_hour: hour })
    onPrefsChange(updated)
    setSaving(false)
  }

  return (
    <div className="p-4 border-t">
      <h2 className="font-semibold text-sm text-gray-500 uppercase tracking-wide mb-3">Schedule</h2>
      <select value={type} onChange={e => setType(e.target.value)}
        className="w-full border rounded px-2 py-1.5 text-sm mb-2">
        <option value="new_episode">On new episodes</option>
        <option value="weekly">Weekly</option>
        <option value="biweekly">Biweekly</option>
      </select>
      {(type === 'weekly' || type === 'biweekly') && (
        <div className="flex gap-2 mb-2">
          <select value={day} onChange={e => setDay(Number(e.target.value))}
            className="flex-1 border rounded px-2 py-1.5 text-sm">
            {DAYS.map((d, i) => <option key={i} value={i}>{d}</option>)}
          </select>
          <select value={hour} onChange={e => setHour(Number(e.target.value))}
            className="flex-1 border rounded px-2 py-1.5 text-sm">
            {Array.from({length: 24}, (_, i) => (
              <option key={i} value={i}>{String(i).padStart(2,'0')}:00</option>
            ))}
          </select>
        </div>
      )}
      <button onClick={save} disabled={saving}
        className="w-full py-1.5 bg-indigo-600 text-white rounded text-sm disabled:opacity-50">
        {saving ? 'Saving...' : 'Save Schedule'}
      </button>
    </div>
  )
}
