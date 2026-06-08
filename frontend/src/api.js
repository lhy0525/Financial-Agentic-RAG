export async function getHealth() {
  return request('/api/health');
}

export async function getPlatform() {
  return request('/api/platform');
}

export async function getHistory() {
  return request('/api/history');
}

export async function clearHistory() {
  return request('/api/history', { method: 'DELETE' });
}

export async function sendChat(question) {
  return request('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
}

export async function uploadProspectus(file) {
  const formData = new FormData();
  formData.append('file', file);
  return request('/api/prospectus/upload', {
    method: 'POST',
    body: formData,
  });
}

async function request(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || `Request failed: ${response.status}`);
  }
  return payload;
}
