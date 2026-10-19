import React, { useState, useEffect } from 'react';
import { X, HardDrive, Copy, Check, Server, Terminal, Shield, ArrowRight } from 'lucide-react';
import { fetchQuickSetupInfo } from '../services/api';

export default function AddNodeModal({ onClose, onRegistered }) {
  const [nodeName, setNodeName] = useState('New Hardware VPS');
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

  const envSnippet = `# MT5 Worker Manager Configuration for ${nodeName}
HUB_URL=${hubUrl}
NODE_ID=${nodeId}
NODE_NAME="${nodeName}"
NODE_API_KEY=${apiKey}

# Path to MT5 template folder on this hardware machine
MASTER_MT5_DIR=C:\\MT5_Master
CLIENTS_DIR=CLIENTS

# Maximum MT5 terminals for this hardware capacity
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
        os_info: 'Remote VPS / Dedicated PC'
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
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '680px' }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <HardDrive size={18} color="var(--accent-cyan)" />
              Add Worker Manager (Scale to New Hardware)
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              Add remote VPS or PC machines to horizontally scale your terminal execution capacity.
            </p>
          </div>
          <button onClick={onClose} className="btn btn-secondary btn-icon" style={{ borderRadius: '50%' }}>
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '24px' }}>
          {/* Node Config Fields */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '14px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: '600' }}>
                Hardware Node Name *
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
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: '600' }}>
                Unique Node ID *
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

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '20px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: '600' }}>
                Max Terminal Slots (Capacity)
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
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: '600' }}>
                Central Hub URL
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

          {/* Quick Setup Instructions */}
          <div style={{
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: '10px',
            border: '1px solid var(--border-subtle)',
            padding: '16px',
            marginBottom: '20px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: '700', color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Terminal size={14} /> Configuration File for New Hardware (.env)
              </span>
              <button
                onClick={handleCopy}
                className="btn btn-secondary"
                style={{ fontSize: '0.74rem', padding: '4px 10px' }}
              >
                {copied ? <Check size={12} color="#10B981" /> : <Copy size={12} />}
                <span>{copied ? 'Copied!' : 'Copy .env snippet'}</span>
              </button>
            </div>
            <pre style={{
              background: '#070B14',
              padding: '12px',
              borderRadius: '6px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.76rem',
              color: '#38BDF8',
              overflowX: 'auto'
            }}>
              {envSnippet}
            </pre>
          </div>

          {/* 3 Steps */}
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: '1.6', marginBottom: '20px' }}>
            <strong style={{ color: 'var(--text-main)', display: 'block', marginBottom: '4px' }}>How to run on the new hardware:</strong>
            <ol style={{ paddingLeft: '20px' }}>
              <li>Copy the <code style={{ color: 'var(--accent-cyan)' }}>worker_node</code> directory to your remote VPS or PC.</li>
              <li>Save the configuration above into <code style={{ color: 'var(--accent-cyan)' }}>worker_node/.env</code>.</li>
              <li>Double-click <code style={{ color: 'var(--accent-cyan)' }}>start_worker.bat</code> or run <code style={{ color: 'var(--accent-cyan)' }}>python worker_manager.py</code>.</li>
            </ol>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              id="btn-register-node"
              type="button"
              className="btn btn-primary"
              onClick={handleRegister}
              disabled={loading}
            >
              <span>{loading ? 'Registering...' : 'Register Hardware Node'}</span>
              <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
