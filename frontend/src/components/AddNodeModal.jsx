import React, { useState, useEffect } from 'react';
import { X, HardDrive, Copy, Check, Terminal, ArrowRight } from 'lucide-react';
import { fetchQuickSetupInfo } from '../services/api';

export default function AddNodeModal({ onClose, onRegistered }) {
  const [nodeName, setNodeName] = useState('New Hardware Node');
  const [nodeId, setNodeId] = useState(`node-${Math.random().toString(36).substring(2, 8)}`);
  const [apiKey, setApiKey] = useState(`key_${Math.random().toString(36).substring(2, 12)}`);
  const [maxTerminals, setMaxTerminals] = useState(30);
  const [hubUrl, setHubUrl] = useState(`http://${window.location.hostname || 'YOUR_SERVER_IP'}:8000`);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchQuickSetupInfo().then(data => {
      if (data?.suggested_node_id) setNodeId(data.suggested_node_id);
      if (data?.api_key) setApiKey(data.api_key);
    }).catch(() => {});
  }, []);

  const envSnippet = `# MT5 Worker Configuration
HUB_URL=${hubUrl}
NODE_ID=${nodeId}
NODE_NAME="${nodeName}"
NODE_API_KEY=${apiKey}
MASTER_MT5_DIR=C:\\MT5_Master
CLIENTS_DIR=CLIENTS
MAX_TERMINALS=${maxTerminals}
POLL_INTERVAL=8
`;

  const handleCopy = () => {
    navigator.clipboard.writeText(envSnippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRegister = async () => {
    try {
      setLoading(true);
      await onRegistered({
        node_id: nodeId,
        name: nodeName,
        api_key: apiKey,
        max_terminals: parseInt(maxTerminals, 10),
        os_info: 'Remote VPS'
      });
      onClose();
    } catch (err) {
      alert('Error registering node: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '620px' }}>
        {/* Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <h3 style={{ fontSize: '1.15rem', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
            <HardDrive size={18} color="var(--accent-indigo)" />
            Add Hardware Node
          </h3>
          <button onClick={onClose} className="btn btn-secondary btn-icon" style={{ borderRadius: '50%' }}>
            <X size={15} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '22px 24px' }}>
          {/* Node Config Fields */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '14px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: '600' }}>
                Node Name *
              </label>
              <input
                type="text"
                className="input-field"
                value={nodeName}
                onChange={(e) => setNodeName(e.target.value)}
                placeholder="e.g. Frankfurt VPS #1"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: '600' }}>
                Node ID *
              </label>
              <input
                type="text"
                className="input-field font-mono"
                value={nodeId}
                onChange={(e) => setNodeId(e.target.value)}
                placeholder="e.g. vps-frankfurt-01"
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: '600' }}>
                Max Capacity (Slots)
              </label>
              <input
                type="number"
                className="input-field font-mono"
                value={maxTerminals}
                onChange={(e) => setMaxTerminals(e.target.value)}
                placeholder="30"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: '600' }}>
                Server URL
              </label>
              <input
                type="text"
                className="input-field font-mono"
                value={hubUrl}
                onChange={(e) => setHubUrl(e.target.value)}
                placeholder="http://192.168.1.100:8000"
              />
            </div>
          </div>

          {/* Quick Setup Snippet */}
          <div style={{
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            padding: '14px',
            marginBottom: '16px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: '600', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Terminal size={13} color="var(--accent-indigo)" /> worker_node/.env
              </span>
              <button
                onClick={handleCopy}
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.72rem', padding: '3px 8px' }}
              >
                {copied ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <pre style={{
              background: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              padding: '10px 12px',
              borderRadius: 'var(--radius-sm)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.74rem',
              color: '#c7d2fe',
              overflowX: 'auto',
              margin: 0
            }}>
              {envSnippet}
            </pre>
          </div>

          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
            Paste into <code style={{ color: 'var(--accent-cyan)' }}>worker_node/.env</code> on the remote machine, then run <code style={{ color: 'var(--accent-cyan)' }}>start_worker.bat</code>.
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
              Cancel
            </button>
            <button
              id="btn-register-node"
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleRegister}
              disabled={loading}
            >
              <span>{loading ? 'Registering...' : 'Register Node'}</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
