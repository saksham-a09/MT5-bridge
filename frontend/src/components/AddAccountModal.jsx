import React, { useState } from 'react';
import { X, Plus, ShieldCheck, Server, AlertCircle } from 'lucide-react';

export default function AddAccountModal({ nodes, onClose, onSave, onSwitchToBulk }) {
  const [formData, setFormData] = useState({
    login: '',
    password: '',
    server: '',
    name: '',
    target_node_id: 'auto',
    expert: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!formData.login || !formData.password || !formData.server) {
      setError('Please provide Login ID, Password, and Broker Server.');
      return;
    }

    try {
      setLoading(true);
      await onSave({
        ...formData,
        login: parseInt(formData.login, 10)
      });
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save account');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: 0 }}>
              Add MetaTrader 5 Account
            </h3>
            <p style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', margin: '2px 0 0' }}>
              Spin up and register a single terminal on the cluster
            </p>
          </div>
          <button onClick={onClose} className="btn btn-secondary btn-icon" style={{ borderRadius: '50%' }}>
            <X size={16} />
          </button>
        </div>

        {/* Tab switch between Single and Bulk */}
        <div style={{ padding: '14px 24px 0', display: 'flex', gap: '8px' }}>
          <button
            type="button"
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.78rem',
              fontWeight: '700',
              cursor: 'pointer',
              border: '1px solid rgba(99, 102, 241, 0.4)',
              background: 'linear-gradient(90deg, rgba(99, 102, 241, 0.22), rgba(6, 182, 212, 0.1))',
              color: '#ffffff'
            }}
          >
            Single Account
          </button>
          <button
            type="button"
            onClick={() => {
              if (onSwitchToBulk) {
                onSwitchToBulk();
              }
            }}
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.78rem',
              fontWeight: '600',
              cursor: 'pointer',
              border: '1px solid var(--border-subtle)',
              background: 'rgba(255, 255, 255, 0.04)',
              color: 'var(--text-secondary)',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = '#ffffff';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--text-secondary)';
              e.currentTarget.style.borderColor = 'var(--border-subtle)';
            }}
          >
            Bulk Import (CSV / Text) →
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: '24px' }}>
          {error && (
            <div style={{
              padding: '12px',
              borderRadius: '8px',
              background: 'rgba(244, 63, 94, 0.15)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              color: '#FB7185',
              fontSize: '0.85rem',
              marginBottom: '18px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: '600' }}>
                MT5 Login ID *
              </label>
              <input
                id="input-login"
                type="number"
                required
                placeholder="e.g. 25506235"
                className="input-field font-mono"
                value={formData.login}
                onChange={(e) => setFormData({ ...formData, login: e.target.value })}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: '600' }}>
                MT5 Password *
              </label>
              <input
                id="input-password"
                type="password"
                required
                placeholder="Account password"
                className="input-field"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              />
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: '600' }}>
              Broker Server Name *
            </label>
            <input
              id="input-server"
              type="text"
              required
              placeholder="e.g. VantageMarkets-Demo, ICMarketsSC-Live01"
              className="input-field"
              value={formData.server}
              onChange={(e) => setFormData({ ...formData, server: e.target.value })}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: '600' }}>
              Account Name / Custom Label
            </label>
            <input
              id="input-name"
              type="text"
              placeholder="e.g. Prop Firm Evaluation #1"
              className="input-field"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: '600' }}>
              Assigned Hardware Node
            </label>
            <select
              id="select-node"
              className="input-field"
              value={formData.target_node_id}
              onChange={(e) => setFormData({ ...formData, target_node_id: e.target.value })}
            >
              <option value="auto">Auto-Balance to Best Node (Recommended)</option>
              {nodes.map(n => (
                <option key={n.node_id} value={n.node_id}>
                  {n.name} ({n.node_id}) - {n.status.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
              Expert EA / Strategy (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. UltraFastCopier (leave blank if none)"
              className="input-field"
              value={formData.expert}
              onChange={(e) => setFormData({ ...formData, expert: e.target.value })}
            />
          </div>

          {/* Footer buttons */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              id="btn-submit-account"
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              <Plus size={16} />
              <span>{loading ? 'Adding...' : 'Save & Spin Up Terminal'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
