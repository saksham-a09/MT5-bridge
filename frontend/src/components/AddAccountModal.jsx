import React, { useState } from 'react';
import { X, Plus, ShieldCheck, Server, AlertCircle } from 'lucide-react';

export default function AddAccountModal({ nodes, onClose, onSave }) {
  const [formData, setFormData] = useState({
    login: '',
    password: '',
    server: '',
    name: '',
    target_node_id: 'auto',
    expert: '',
    symbol: 'XAUUSD',
    timeframe: 'M1'
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
          padding: '20px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: '800' }}>
              Add MetaTrader 5 Account
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              Credentials are saved in the DB and dispatched to an online worker manager.
            </p>
          </div>
          <button onClick={onClose} className="btn btn-secondary btn-icon" style={{ borderRadius: '50%' }}>
            <X size={16} />
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
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '4px', display: 'block' }}>
              Auto-balancing automatically selects the hardware node with the most available slots.
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '24px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Expert EA (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. UltraFastCopier"
                className="input-field"
                value={formData.expert}
                onChange={(e) => setFormData({ ...formData, expert: e.target.value })}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Default Symbol
              </label>
              <input
                type="text"
                placeholder="XAUUSD"
                className="input-field font-mono"
                value={formData.symbol}
                onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Timeframe
              </label>
              <select
                className="input-field font-mono"
                value={formData.timeframe}
                onChange={(e) => setFormData({ ...formData, timeframe: e.target.value })}
              >
                <option value="M1">M1</option>
                <option value="M5">M5</option>
                <option value="M15">M15</option>
                <option value="H1">H1</option>
                <option value="H4">H4</option>
                <option value="D1">D1</option>
              </select>
            </div>
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
