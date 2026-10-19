import React, { useState } from 'react';
import { 
  Users, Copy, Play, Pause, Trash2, Plus, ArrowRight, Shield, 
  Zap, CheckCircle2, AlertCircle, RefreshCw, Layers, TrendingUp,
  Percent, DollarSign, Clock, Settings
} from 'lucide-react';

export default function CopyTradingView({ 
  groups = [], 
  accounts = [], 
  copiedTrades = [], 
  onRefresh, 
  onCreateGroup, 
  onUpdateGroup, 
  onDeleteGroup, 
  onAddSlave, 
  onRemoveSlave,
  onTriggerSync 
}) {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedGroupForSlave, setSelectedGroupForSlave] = useState(null);
  const [activeTab, setActiveTab] = useState('groups'); // 'groups' | 'trades'

  // New Group Form State
  const [formData, setFormData] = useState({
    name: '',
    master_login: '',
    risk_type: 'multiplier',
    multiplier: 1.0,
    fixed_lot: 0.01,
    max_slippage_points: 20,
    copy_sl_tp: true,
    copy_pending_orders: true,
    selected_slaves: []
  });

  // Add Slave Form State
  const [slaveLoginToAdd, setSlaveLoginToAdd] = useState('');
  const [slaveMultiplierOverride, setSlaveMultiplierOverride] = useState('');

  const handleOpenCreate = () => {
    const firstAcc = accounts[0]?.login || '';
    setFormData({
      name: 'Vantage Alpha Copy Group',
      master_login: firstAcc ? String(firstAcc) : '',
      risk_type: 'multiplier',
      multiplier: 1.0,
      fixed_lot: 0.01,
      max_slippage_points: 20,
      copy_sl_tp: true,
      copy_pending_orders: true,
      selected_slaves: accounts.filter(a => String(a.login) !== String(firstAcc)).map(a => a.login)
    });
    setShowCreateModal(true);
  };

  const handleMasterChange = (masterId) => {
    setFormData(prev => ({
      ...prev,
      master_login: masterId,
      selected_slaves: prev.selected_slaves.filter(s => String(s) !== String(masterId))
    }));
  };

  const handleToggleSlave = (login) => {
    setFormData(prev => {
      const exists = prev.selected_slaves.includes(login);
      return {
        ...prev,
        selected_slaves: exists 
          ? prev.selected_slaves.filter(s => s !== login)
          : [...prev.selected_slaves, login]
      };
    });
  };

  const handleSubmitCreate = async (e) => {
    e.preventDefault();
    if (!formData.name || !formData.master_login) return;

    await onCreateGroup({
      name: formData.name,
      master_login: parseInt(formData.master_login),
      risk_type: formData.risk_type,
      multiplier: parseFloat(formData.multiplier) || 1.0,
      fixed_lot: parseFloat(formData.fixed_lot) || 0.01,
      max_slippage_points: parseInt(formData.max_slippage_points) || 20,
      copy_sl_tp: formData.copy_sl_tp,
      copy_pending_orders: formData.copy_pending_orders,
      initial_slave_logins: formData.selected_slaves.map(s => parseInt(s))
    });

    setShowCreateModal(false);
  };

  const handleAddSlaveSubmit = async (e) => {
    e.preventDefault();
    if (!selectedGroupForSlave || !slaveLoginToAdd) return;

    await onAddSlave(selectedGroupForSlave.id, {
      slave_login: parseInt(slaveLoginToAdd),
      custom_multiplier: slaveMultiplierOverride ? parseFloat(slaveMultiplierOverride) : null
    });

    setSelectedGroupForSlave(null);
    setSlaveLoginToAdd('');
    setSlaveMultiplierOverride('');
  };

  return (
    <div className="copy-trading-container">
      {/* Top Banner / Actions */}
      <div className="copier-header-bar">
        <div>
          <h2 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Zap className="text-amber" size={24} />
            Distributed Trade Copier
          </h2>
          <p className="text-muted" style={{ fontSize: '0.85rem' }}>
            Ultra-low latency master-to-slave trade mirroring with automatic lot scaling and exact order matching.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.6rem' }}>
          <button 
            className="btn btn-secondary" 
            onClick={onTriggerSync}
            title="Force immediate synchronization across all groups"
          >
            <RefreshCw size={15} />
            <span>Sync Now</span>
          </button>

          <button className="btn btn-primary" onClick={handleOpenCreate}>
            <Plus size={16} />
            <span>New Copy Group</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="copier-tabs">
        <button 
          className={`tab-btn ${activeTab === 'groups' ? 'active' : ''}`}
          onClick={() => setActiveTab('groups')}
        >
          <Layers size={16} />
          <span>Active Groups ({groups.length})</span>
        </button>

        <button 
          className={`tab-btn ${activeTab === 'trades' ? 'active' : ''}`}
          onClick={() => setActiveTab('trades')}
        >
          <TrendingUp size={16} />
          <span>Copied Trades History ({copiedTrades.length})</span>
        </button>
      </div>

      {activeTab === 'groups' ? (
        <div className="copier-groups-list">
          {groups.length === 0 ? (
            <div className="empty-copier-state">
              <Copy size={48} className="text-muted" />
              <h3>No Copy Trading Groups Yet</h3>
              <p>Create a group to link a Master MT5 account with one or more Slave terminals to begin instant trade replication.</p>
              <button className="btn btn-primary" onClick={handleOpenCreate} style={{ marginTop: '1rem' }}>
                <Plus size={16} />
                <span>Create Your First Group</span>
              </button>
            </div>
          ) : (
            groups.map(grp => {
              const isGroupActive = grp.status === 'active';
              return (
                <div key={grp.id} className={`group-card ${isGroupActive ? 'active-border' : 'paused-border'}`}>
                  {/* Group Header */}
                  <div className="group-card-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <div className="group-badge-icon">
                        <Zap size={18} />
                      </div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className="group-title">{grp.name}</span>
                          <span className={`status-pill ${isGroupActive ? 'online' : 'offline'}`}>
                            {grp.status.toUpperCase()}
                          </span>
                        </div>
                        <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                          Group #{grp.id} • Max Slippage: {grp.max_slippage_points} pts • SL/TP: {grp.copy_sl_tp ? 'Copied' : 'Ignored'}
                        </span>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <button 
                        className={`btn-icon ${isGroupActive ? 'btn-icon-pause' : 'btn-icon-play'}`}
                        onClick={() => onUpdateGroup(grp.id, { status: isGroupActive ? 'paused' : 'active' })}
                        title={isGroupActive ? 'Pause trade copying' : 'Resume trade copying'}
                      >
                        {isGroupActive ? <Pause size={15} /> : <Play size={15} />}
                      </button>

                      <button 
                        className="btn-icon btn-icon-delete"
                        onClick={() => onDeleteGroup(grp.id)}
                        title="Delete copy group"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>

                  {/* Flow Diagram (Master -> Slaves) */}
                  <div className="group-flow-container">
                    {/* Master Box */}
                    <div className="role-box master-box">
                      <div className="role-header">
                        <span className="master-crown">👑 MASTER</span>
                        <span className="acc-login-tag">{grp.master_login}</span>
                      </div>
                      <div className="role-body">
                        <div className="role-name">{grp.master_name || 'Master Account'}</div>
                        <div className="role-sub text-muted">{grp.master_server}</div>
                      </div>
                    </div>

                    {/* Arrow with Risk Mode Tag */}
                    <div className="flow-arrow-col">
                      <span className="risk-mode-tag">
                        {grp.risk_type === 'multiplier' && `${grp.multiplier}x Multiplier`}
                        {grp.risk_type === 'equity_ratio' && `Equity Proportional`}
                        {grp.risk_type === 'balance_ratio' && `Balance Proportional`}
                        {grp.risk_type === 'fixed_lot' && `${grp.fixed_lot} Fixed Lots`}
                      </span>
                      <div className="arrow-line">
                        <ArrowRight size={20} className="arrow-icon" />
                      </div>
                      <span className="latency-est">Sub-100ms Mirror</span>
                    </div>

                    {/* Slaves List Box */}
                    <div className="role-box slaves-box">
                      <div className="role-header">
                        <span>SLAVES ({grp.slaves?.length || 0})</span>
                        <button 
                          className="btn-xs-add" 
                          onClick={() => setSelectedGroupForSlave(grp)}
                          title="Attach another slave account"
                        >
                          <Plus size={12} /> Add Slave
                        </button>
                      </div>

                      <div className="slaves-scroll-list">
                        {(!grp.slaves || grp.slaves.length === 0) ? (
                          <div className="no-slaves-text">No slave terminals assigned. Click "+ Add Slave" above.</div>
                        ) : (
                          grp.slaves.map(slv => (
                            <div key={slv.slave_login} className="slave-row-item">
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
                                <span className={`dot-status ${slv.is_connected ? 'online' : 'offline'}`} />
                                <span className="slave-login-num">{slv.slave_login}</span>
                                <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                                  ({slv.slave_name || 'Slave'})
                                </span>
                                {slv.error_message && slv.error_message.toLowerCase().includes('autotrading') && (
                                  <span style={{ fontSize: '0.7rem', color: '#f59e0b', background: 'rgba(245, 158, 11, 0.15)', padding: '1px 6px', borderRadius: '4px', fontWeight: 600 }}>
                                    ⚠️ Click 'Algo Trading' (Ctrl+E)
                                  </span>
                                )}
                              </div>

                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                {slv.custom_multiplier && (
                                  <span className="custom-mult-badge">{slv.custom_multiplier}x</span>
                                )}
                                <button 
                                  className="btn-remove-slave" 
                                  onClick={() => onRemoveSlave(grp.id, slv.slave_login)}
                                  title="Detach slave from this group"
                                >
                                  ×
                                </button>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Group Footer Metrics */}
                  <div className="group-metrics-footer">
                    <div className="metric-col">
                      <span className="text-muted">Active Copied Positions:</span>
                      <span className="metric-val">{grp.open_copied_trades_count || 0}</span>
                    </div>
                    <div className="metric-col">
                      <span className="text-muted">Total Slave Profit:</span>
                      <span className={`metric-val ${(grp.total_slave_profit || 0) >= 0 ? 'text-green' : 'text-red'}`}>
                        ${(grp.total_slave_profit || 0).toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      ) : (
        /* Copied Trades Live Table */
        <div className="copied-trades-table-card">
          <div className="table-wrapper">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Trade ID</th>
                  <th>Group</th>
                  <th>Master Ticket</th>
                  <th>Slave Login / Ticket</th>
                  <th>Symbol</th>
                  <th>Type</th>
                  <th>Master Vol</th>
                  <th>Slave Vol</th>
                  <th>Execution Delay</th>
                  <th>Slave Profit</th>
                  <th>Status</th>
                  <th>Opened At</th>
                </tr>
              </thead>
              <tbody>
                {copiedTrades.length === 0 ? (
                  <tr>
                    <td colSpan="12" style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
                      No copied trades recorded yet. Once Master opens a trade, slave mirror trades will appear here in real-time.
                    </td>
                  </tr>
                ) : (
                  copiedTrades.map(trade => {
                    const isBuy = trade.order_type === 'BUY';
                    return (
                      <tr key={trade.id}>
                        <td><span className="mono-ticket">#{trade.id}</span></td>
                        <td><span className="group-tag">{trade.group_name || `Group #${trade.group_id}`}</span></td>
                        <td><span className="mono-ticket text-amber">#{trade.master_ticket}</span></td>
                        <td>
                          <div>
                            <span className="slave-id">{trade.slave_login}</span>
                            <span className="text-muted" style={{ fontSize: '0.75rem', marginLeft: '0.3rem' }}>
                              #{trade.slave_ticket}
                            </span>
                          </div>
                        </td>
                        <td><strong>{trade.symbol}</strong></td>
                        <td>
                          <span className={`pill-order ${isBuy ? 'pill-buy' : 'pill-sell'}`}>
                            {trade.order_type}
                          </span>
                        </td>
                        <td>{trade.master_volume}</td>
                        <td><strong className="text-cyan">{trade.slave_volume}</strong></td>
                        <td>
                          <span className="latency-badge">
                            <Clock size={11} /> {trade.execution_ms || '<25'}ms
                          </span>
                        </td>
                        <td>
                          <span className={(trade.slave_profit || 0) >= 0 ? 'text-green' : 'text-red'}>
                            ${(trade.slave_profit || 0).toFixed(2)}
                          </span>
                        </td>
                        <td>
                          <span className={`status-badge ${trade.status === 'open' ? 'badge-open' : 'badge-closed'}`}>
                            {trade.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="text-muted" style={{ fontSize: '0.75rem' }}>
                          {trade.opened_at ? new Date(trade.opened_at).toLocaleTimeString() : '-'}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CREATE GROUP MODAL */}
      {showCreateModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <Zap className="text-amber" size={20} />
                <h3 className="modal-title">Create Copy Trading Group</h3>
              </div>
              <button className="btn-close" onClick={() => setShowCreateModal(false)}>×</button>
            </div>

            <form onSubmit={handleSubmitCreate}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Group Name</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    required 
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Master Gold Scalper Group"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Select Master Account</label>
                  <select 
                    className="form-control"
                    value={formData.master_login}
                    onChange={(e) => handleMasterChange(e.target.value)}
                    required
                  >
                    {accounts.map(acc => (
                      <option key={acc.login} value={acc.login}>
                        {acc.login} - {acc.name || 'Account'} ({acc.server}) [${acc.balance || 0}]
                      </option>
                    ))}
                  </select>
                  <small className="form-hint">Trades opened on this Master will be copied to all selected slaves.</small>
                </div>

                <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">Volume Sizing Mode</label>
                    <select 
                      className="form-control"
                      value={formData.risk_type}
                      onChange={(e) => setFormData({ ...formData, risk_type: e.target.value })}
                    >
                      <option value="multiplier">Fixed Multiplier (e.g. 1.0x)</option>
                      <option value="equity_ratio">Equity Proportional (Risk Balanced)</option>
                      <option value="balance_ratio">Balance Proportional</option>
                      <option value="fixed_lot">Fixed Lot Size</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">
                      {formData.risk_type === 'fixed_lot' ? 'Fixed Lot Size' : 'Multiplier Factor'}
                    </label>
                    <input 
                      type="number" 
                      step="0.01" 
                      min="0.01"
                      className="form-control"
                      value={formData.risk_type === 'fixed_lot' ? formData.fixed_lot : formData.multiplier}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value) || 0.01;
                        if (formData.risk_type === 'fixed_lot') {
                          setFormData({ ...formData, fixed_lot: val });
                        } else {
                          setFormData({ ...formData, multiplier: val });
                        }
                      }}
                    />
                  </div>
                </div>

                <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">Max Slippage (Points)</label>
                    <input 
                      type="number" 
                      min="1" 
                      max="100"
                      className="form-control"
                      value={formData.max_slippage_points}
                      onChange={(e) => setFormData({ ...formData, max_slippage_points: parseInt(e.target.value) || 20 })}
                    />
                  </div>

                  <div className="form-group" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginTop: '1rem' }}>
                      <input 
                        type="checkbox" 
                        checked={formData.copy_sl_tp}
                        onChange={(e) => setFormData({ ...formData, copy_sl_tp: e.target.checked })}
                      />
                      <span>Mirror Stop Loss & Take Profit</span>
                    </label>
                  </div>
                </div>

                {/* Slave Selection */}
                <div className="form-group" style={{ marginTop: '0.5rem' }}>
                  <label className="form-label">Assign Slave Accounts</label>
                  <div className="slave-select-container">
                    {accounts.filter(a => String(a.login) !== String(formData.master_login)).length === 0 ? (
                      <div className="text-muted" style={{ fontSize: '0.8rem', padding: '0.5rem' }}>
                        No other accounts available to act as slaves. Add more accounts first.
                      </div>
                    ) : (
                      accounts
                        .filter(a => String(a.login) !== String(formData.master_login))
                        .map(acc => {
                          const checked = formData.selected_slaves.includes(acc.login);
                          return (
                            <label key={acc.login} className={`slave-select-card ${checked ? 'selected' : ''}`}>
                              <input 
                                type="checkbox" 
                                checked={checked}
                                onChange={() => handleToggleSlave(acc.login)}
                              />
                              <div>
                                <div style={{ fontWeight: 600 }}>{acc.login} - {acc.name || 'Account'}</div>
                                <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                                  {acc.server} • Balance: ${acc.balance || 0}
                                </div>
                              </div>
                            </label>
                          );
                        })
                    )}
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create Group
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ADD SLAVE MODAL */}
      {selectedGroupForSlave && (
        <div className="modal-backdrop">
          <div className="modal-dialog" style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Attach Slave to {selectedGroupForSlave.name}</h3>
              <button className="btn-close" onClick={() => setSelectedGroupForSlave(null)}>×</button>
            </div>

            <form onSubmit={handleAddSlaveSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Select Slave Account</label>
                  <select 
                    className="form-control"
                    required
                    value={slaveLoginToAdd}
                    onChange={(e) => setSlaveLoginToAdd(e.target.value)}
                  >
                    <option value="">-- Choose Account --</option>
                    {accounts
                      .filter(a => 
                        a.login !== selectedGroupForSlave.master_login &&
                        !(selectedGroupForSlave.slaves || []).some(s => s.slave_login === a.login)
                      )
                      .map(acc => (
                        <option key={acc.login} value={acc.login}>
                          {acc.login} ({acc.server}) - Balance: ${acc.balance || 0}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Custom Multiplier Override (Optional)</label>
                  <input 
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="Leave empty to use group default"
                    className="form-control"
                    value={slaveMultiplierOverride}
                    onChange={(e) => setSlaveMultiplierOverride(e.target.value)}
                  />
                  <small className="form-hint">E.g. set to 2.0 to double lot size specifically for this slave account.</small>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setSelectedGroupForSlave(null)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Attach Slave
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
