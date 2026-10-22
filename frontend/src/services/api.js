const API_BASE = '/api';

export async function fetchDashboardStats() {
  const res = await fetch(`${API_BASE}/dashboard/stats`);
  return res.json();
}

export async function fetchAccounts(status = 'all', search = '') {
  const params = new URLSearchParams();
  if (status && status !== 'all') params.append('status', status);
  if (search) params.append('search', search);
  const res = await fetch(`${API_BASE}/accounts?${params.toString()}`);
  return res.json();
}

export async function fetchAccount(login) {
  const res = await fetch(`${API_BASE}/accounts/${login}`);
  return res.json();
}

export async function createAccount(payload) {
  const res = await fetch(`${API_BASE}/accounts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return res.json();
}

export async function createAccountsBulk(payload) {
  const res = await fetch(`${API_BASE}/accounts/bulk`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return res.json();
}

export async function updateAccount(login, payload) {
  const res = await fetch(`${API_BASE}/accounts/${login}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return res.json();
}

export async function deleteAccount(login) {
  const res = await fetch(`${API_BASE}/accounts/${login}`, {
    method: 'DELETE'
  });
  return res.json();
}

export async function startAccount(login) {
  const res = await fetch(`${API_BASE}/accounts/${login}/start`, {
    method: 'POST'
  });
  return res.json();
}

export async function stopAccount(login) {
  const res = await fetch(`${API_BASE}/accounts/${login}/stop`, {
    method: 'POST'
  });
  return res.json();
}

export async function restartAccount(login) {
  const res = await fetch(`${API_BASE}/accounts/${login}/restart`, {
    method: 'POST'
  });
  return res.json();
}

export async function fetchNodes() {
  const res = await fetch(`${API_BASE}/nodes`);
  return res.json();
}

export async function registerNode(payload) {
  const res = await fetch(`${API_BASE}/nodes/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return res.json();
}

export async function deleteNode(nodeId) {
  const res = await fetch(`${API_BASE}/nodes/${nodeId}`, {
    method: 'DELETE'
  });
  return res.json();
}

export async function fetchQuickSetupInfo() {
  const res = await fetch(`${API_BASE}/nodes/quick-setup`);
  return res.json();
}

export async function fetchLogs(limit = 40) {
  const res = await fetch(`${API_BASE}/dashboard/logs?limit=${limit}`);
  return res.json();
}

// Copy Trading API
export async function fetchCopyGroups() {
  const res = await fetch(`${API_BASE}/copier/groups`);
  return res.json();
}

export async function createCopyGroup(payload) {
  const res = await fetch(`${API_BASE}/copier/groups`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return res.json();
}

export async function updateCopyGroup(groupId, payload) {
  const res = await fetch(`${API_BASE}/copier/groups/${groupId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return res.json();
}

export async function deleteCopyGroup(groupId) {
  const res = await fetch(`${API_BASE}/copier/groups/${groupId}`, {
    method: 'DELETE'
  });
  return res.json();
}

export async function addSlaveToGroup(groupId, payload) {
  const res = await fetch(`${API_BASE}/copier/groups/${groupId}/slaves`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return res.json();
}

export async function removeSlaveFromGroup(groupId, slaveLogin) {
  const res = await fetch(`${API_BASE}/copier/groups/${groupId}/slaves/${slaveLogin}`, {
    method: 'DELETE'
  });
  return res.json();
}

export async function fetchCopiedTrades(groupId = null, limit = 50) {
  const url = groupId 
    ? `${API_BASE}/copier/trades?group_id=${groupId}&limit=${limit}`
    : `${API_BASE}/copier/trades?limit=${limit}`;
  const res = await fetch(url);
  return res.json();
}

export async function triggerCopierSync() {
  const res = await fetch(`${API_BASE}/copier/trigger-sync`, { method: 'POST' });
  return res.json();
}

export function createDashboardWebSocket(onMessage, onError) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  
  let ws = null;
  let reconnectTimer = null;

  function connect() {
    ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (err) {
        console.error('WS parse error:', err);
      }
    };

    ws.onclose = () => {
      if (onError) onError('disconnected');
      reconnectTimer = setTimeout(connect, 3000);
    };

    ws.onerror = (err) => {
      if (onError) onError(err);
      ws.close();
    };
  }

  connect();

  return {
    close: () => {
      clearTimeout(reconnectTimer);
      if (ws) ws.close();
    }
  };
}
