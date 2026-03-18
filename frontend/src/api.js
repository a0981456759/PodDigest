const BASE = '/api'

export async function getShows() {
  const r = await fetch(`${BASE}/shows`)
  return r.json()
}

export async function searchShows(query) {
  const r = await fetch(`${BASE}/shows/search`, {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ query })
  })
  return r.json()
}

export async function addShow(rss_url) {
  const r = await fetch(`${BASE}/shows`, {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ rss_url })
  })
  if (!r.ok) throw new Error((await r.json()).detail)
  return r.json()
}

export async function importOpml(file) {
  const form = new FormData()
  form.append('file', file)
  const r = await fetch(`${BASE}/shows/import-opml`, { method: 'POST', body: form })
  return r.json()
}

export async function deleteShow(id) {
  await fetch(`${BASE}/shows/${id}`, { method: 'DELETE' })
}

export async function getDigests() {
  const r = await fetch(`${BASE}/digests`)
  return r.json()
}

export async function triggerDigest() {
  const r = await fetch(`${BASE}/digest/trigger`, { method: 'POST' })
  if (!r.ok) throw new Error((await r.json()).detail)
  return r.json()
}

export async function getPreferences() {
  const r = await fetch(`${BASE}/preferences`)
  return r.json()
}

export async function updatePreferences(data) {
  const r = await fetch(`${BASE}/preferences`, {
    method: 'PUT', headers: {'Content-Type':'application/json'},
    body: JSON.stringify(data)
  })
  return r.json()
}

export function streamJob(jobId, onEvent) {
  const es = new EventSource(`/api/digest/jobs/${jobId}/stream`)
  es.onmessage = (e) => {
    const event = JSON.parse(e.data)
    onEvent(event)
    if (event.step === 'done' || event.step === 'failed') es.close()
  }
  es.onerror = () => es.close()
  return es
}
