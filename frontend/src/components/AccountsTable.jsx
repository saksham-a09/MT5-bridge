import React, { useState, useRef, useEffect } from 'react';
import { 
  Play, Square, RotateCw, Trash2, ExternalLink, Search, 
  Layers, Clock, Upload, CheckSquare, XSquare, XCircle
} from 'lucide-react';

export default function AccountsTable({ 
  accounts, 
  search, 
  setSearch, 
  statusFilter, 
  setStatusFilter, 
  nodeFilter, 
  setNodeFilter,
  onStart, 
  onStop, 
  onRestart, 
  onDelete, 
  onSelectAccount,
  onBulkImport,
  onBatchAction,
  nodes = []
}) {
  const [selectedLogins, setSelectedLogins] = useState([]);
  const headerCheckboxRef = useRef(null);
  // Filter accounts
  const filtered = accounts.filter(acc => {
    // Node filter
    if (nodeFilter && acc.assigned_node_id !== nodeFilter) return false;
    
    // Status filter
    if (statusFilter === 'connected' && !acc.is_connected) return false;
    if (statusFilter === 'active' && acc.status !== 'active') return false;
    if (statusFilter === 'stopped' && acc.status !== 'stopped') return false;

    // Search
    if (search) {
      const q = search.toLowerCase();
      const loginStr = String(acc.login);
      const name = (acc.name || '').toLowerCase();
      const server = (acc.server || '').toLowerCase();
      const broker = (acc.broker_name || '').toLowerCase();
      if (!loginStr.includes(q) && !name.includes(q) && !server.includes(q) && !broker.includes(q)) {
        return false;
      }
    }
    return true;
  });

  const filteredLogins = filtered.map(a => a.login);
  const allFilteredSelected = filteredLogins.length > 0 && filteredLogins.every(l => selectedLogins.includes(l));
  const someFilteredSelected = filteredLogins.some(l => selectedLogins.includes(l));

  useEffect(() => {
    if (headerCheckboxRef.current) {
      headerCheckboxRef.current.indeterminate = someFilteredSelected && !allFilteredSelected;
    }
  }, [someFilteredSelected, allFilteredSelected]);

  const handleSelectAll = () => {
    if (allFilteredSelected) {
      setSelectedLogins(prev => prev.filter(l => !filteredLogins.includes(l)));
    } else {
      setSelectedLogins(prev => Array.from(new Set([...prev, ...filteredLogins])));
    }
  };

  const handleToggleSelect = (login) => {
    setSelectedLogins(prev => 
      prev.includes(login) ? prev.filter(l => l !== login) : [...prev, login]
    );
  };

  return (
    <div className="glass-card" style={{ padding: '24px' }}>
      {/* Controls Bar */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        marginBottom: '20px'
      }}>
        {/* Title & Active Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h2 style={{ fontSize: '1.15rem', fontWeight: '700', letterSpacing: '-0.01em' }}>
            Managed MT5 Accounts
          </h2>
          <span style={{
            fontSize: '0.75rem',
            padding: '2px 8px',
            borderRadius: 'var(--radius-full)',
            background: 'rgba(255, 255, 255, 0.08)',
            color: 'var(--text-secondary)',
            fontWeight: '600'
          }}>
            {filtered.length} of {accounts.length}
          </span>
          {nodeFilter && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.3)', padding: '2px 8px', borderRadius: '4px' }}>
              <span style={{ fontSize: '0.75rem', color: '#c7d2fe' }}>Node: {nodeFilter}</span>
              <button
                onClick={() => setNodeFilter(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.85rem' }}
              >
                ×
              </button>
            </div>
          )}
        </div>

        {/* Search & Status Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Status Pills */}
          <div style={{ display: 'flex', background: 'rgba(0, 0, 0, 0.3)', padding: '3px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            {[
              { id: 'all', label: 'All' },
              { id: 'active', label: 'Active' },
              { id: 'connected', label: 'Connected' },
              { id: 'stopped', label: 'Stopped' }
            ].map(tab => {
              const isActive = statusFilter === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setStatusFilter(tab.id)}
                  style={{
                    background: isActive ? 'linear-gradient(90deg, rgba(99, 102, 241, 0.22), rgba(6, 182, 212, 0.1))' : 'transparent',
                    color: isActive ? '#ffffff' : 'var(--text-secondary)',
                    border: isActive ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
                    padding: '5px 12px',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.78rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    boxShadow: isActive ? '0 2px 6px rgba(0, 0, 0, 0.3)' : 'none'
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Search Box */}
          <div style={{ position: 'relative', width: '220px' }}>
            <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Search login, server..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field"
              style={{ paddingLeft: '32px', fontSize: '0.8rem', height: '34px' }}
            />
          </div>

          {/* Bulk Import Action Button */}
          {onBulkImport && (
            <button
              id="btn-table-bulk-import"
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onBulkImport}
              title="Bulk import multiple accounts from CSV or text"
              style={{
                borderColor: 'rgba(6, 182, 212, 0.4)',
                color: 'var(--accent-cyan)',
                height: '34px',
                padding: '0 12px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <Upload size={13} />
              <span>Bulk Import</span>
            </button>
          )}
        </div>
      </div>

      {/* Batch Actions Toolbar */}
      {selectedLogins.length > 0 && (
        <div style={{
          marginBottom: '16px',
          padding: '10px 16px',
          borderRadius: 'var(--radius-md)',
          background: 'linear-gradient(90deg, rgba(99, 102, 241, 0.16), rgba(6, 182, 212, 0.1))',
          border: '1px solid rgba(99, 102, 241, 0.4)',
          boxShadow: '0 4px 14px rgba(0, 0, 0, 0.35)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          {/* Left Selection Info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{
              fontSize: '0.8rem',
              fontWeight: '700',
              color: '#ffffff',
              background: 'rgba(99, 102, 241, 0.3)',
              border: '1px solid rgba(99, 102, 241, 0.5)',
              padding: '3px 10px',
              borderRadius: 'var(--radius-full)'
            }}>
              {selectedLogins.length} {selectedLogins.length === 1 ? 'Account' : 'Accounts'} Selected
            </span>
            <button
              type="button"
              onClick={handleSelectAll}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-cyan)',
                cursor: 'pointer',
                fontSize: '0.78rem',
                textDecoration: 'underline'
              }}
            >
              {allFilteredSelected ? 'Deselect visible' : `Select all visible (${filtered.length})`}
            </button>
            <span style={{ color: 'var(--border-subtle)' }}>•</span>
            <button
              type="button"
              onClick={() => setSelectedLogins([])}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '0.78rem'
              }}
            >
              Clear
            </button>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {/* Batch Start */}
            <button
              id="btn-batch-start"
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                if (onBatchAction) onBatchAction(selectedLogins, 'start');
              }}
              style={{ borderColor: 'rgba(16, 185, 129, 0.4)', color: '#34d399', fontSize: '0.78rem', padding: '5px 12px' }}
              title="Start / activate selected terminals"
            >
              <Play size={13} fill="currentColor" />
              <span>Start ({selectedLogins.length})</span>
            </button>

            {/* Batch Stop */}
            <button
              id="btn-batch-stop"
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                if (onBatchAction) onBatchAction(selectedLogins, 'stop');
              }}
              style={{ borderColor: 'rgba(245, 158, 11, 0.4)', color: '#fbbf24', fontSize: '0.78rem', padding: '5px 12px' }}
              title="Stop selected terminals"
            >
              <Square size={12} fill="currentColor" />
              <span>Stop</span>
            </button>

            {/* Batch Restart */}
            <button
              id="btn-batch-restart"
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                if (onBatchAction) onBatchAction(selectedLogins, 'restart');
              }}
              style={{ borderColor: 'rgba(99, 102, 241, 0.4)', color: '#c7d2fe', fontSize: '0.78rem', padding: '5px 12px' }}
              title="Restart selected terminals"
            >
              <RotateCw size={12} />
              <span>Restart</span>
            </button>

            {/* Batch Close Positions */}
            <button
              id="btn-batch-close-positions"
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                if (onBatchAction) onBatchAction(selectedLogins, 'close_all_positions');
              }}
              style={{ borderColor: 'rgba(244, 63, 94, 0.4)', color: '#fb7185', fontSize: '0.78rem', padding: '5px 12px' }}
              title="Emergency close all open positions on selected accounts"
            >
              <XCircle size={12} />
              <span>Close Positions</span>
            </button>

            {/* Batch Cancel Orders */}
            <button
              id="btn-batch-cancel-orders"
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                if (onBatchAction) onBatchAction(selectedLogins, 'cancel_all_orders');
              }}
              style={{ borderColor: 'rgba(245, 158, 11, 0.4)', color: '#fbbf24', fontSize: '0.78rem', padding: '5px 12px' }}
              title="Cancel all pending orders on selected accounts"
            >
              <Clock size={12} />
              <span>Cancel Orders</span>
            </button>

            {/* Move to Node */}
            {nodes && nodes.length > 0 && (
              <select
                id="select-batch-node"
                onChange={(e) => {
                  if (e.target.value && onBatchAction) {
                    onBatchAction(selectedLogins, 'assign_node', e.target.value);
                    e.target.value = '';
                  }
                }}
                defaultValue=""
                className="input-field"
                style={{ height: '31px', fontSize: '0.76rem', width: 'auto', padding: '2px 8px', background: 'rgba(15, 23, 42, 0.85)' }}
                title="Move selected accounts to hardware node"
              >
                <option value="" disabled>Move Node...</option>
                <option value="auto">Auto-Balance</option>
                {nodes.map(n => (
                  <option key={n.node_id} value={n.node_id}>
                    {n.name}
                  </option>
                ))}
              </select>
            )}

            {/* Batch Delete */}
            <button
              id="btn-batch-delete"
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                if (onBatchAction) {
                  onBatchAction(selectedLogins, 'delete');
                  setSelectedLogins([]);
                }
              }}
              style={{ borderColor: 'rgba(244, 63, 94, 0.4)', color: '#fb7185', fontSize: '0.78rem', padding: '5px 12px' }}
              title="Delete selected accounts from cluster"
            >
              <Trash2 size={12} />
              <span>Delete</span>
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{
              background: 'rgba(10, 16, 29, 0.85)',
              borderBottom: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
              fontSize: '0.74rem',
              fontWeight: '700',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              <th style={{ padding: '12px 14px', width: '38px', textAlign: 'center' }}>
                <input
                  ref={headerCheckboxRef}
                  type="checkbox"
                  checked={allFilteredSelected}
                  onChange={handleSelectAll}
                  style={{ cursor: 'pointer', width: '15px', height: '15px', accentColor: 'var(--accent-indigo)' }}
                  title={allFilteredSelected ? 'Deselect all' : 'Select all'}
                />
              </th>
              <th style={{ padding: '12px 16px' }}>Account</th>
              <th style={{ padding: '12px 16px' }}>Broker & Server</th>
              <th style={{ padding: '12px 16px' }}>Assigned Hardware</th>
              <th style={{ padding: '12px 16px' }}>Status</th>
              <th style={{ padding: '12px 16px' }}>Balance</th>
              <th style={{ padding: '12px 16px' }}>Equity</th>
              <th style={{ padding: '12px 16px' }}>Floating P/L</th>
              <th style={{ padding: '12px 16px' }}>Margin Free</th>
              <th style={{ padding: '12px 16px' }}>Orders</th>
              <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan="11" style={{ padding: '48px 20px', textAlign: 'center' }}>
                  <div style={{ maxWidth: '380px', margin: '0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
                    <div style={{
                      width: '44px',
                      height: '44px',
                      borderRadius: '50%',
                      background: 'rgba(255, 255, 255, 0.04)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--text-muted)'
                    }}>
                      <Layers size={22} />
                    </div>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: 0 }}>
                      No MT5 accounts match the selected criteria.
                    </p>
                    {onBulkImport && (
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={onBulkImport}
                        style={{ borderColor: 'rgba(99, 102, 241, 0.3)', color: '#c7d2fe', marginTop: '6px' }}
                      >
                        <Upload size={13} />
                        <span>Bulk Import Accounts</span>
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map(acc => {
                const isConn = Boolean(acc.is_connected);
                const isStopped = acc.status === 'stopped';
                const profit = acc.profit || 0;
                const isProfitPos = profit >= 0;

                return (
                  <tr
                    key={acc.login}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      transition: 'background 0.15s ease',
                      background: selectedLogins.includes(acc.login) ? 'rgba(99, 102, 241, 0.08)' : 'transparent'
                    }}
                    onMouseEnter={(e) => {
                      if (!selectedLogins.includes(acc.login)) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.025)';
                    }}
                    onMouseLeave={(e) => {
                      if (!selectedLogins.includes(acc.login)) e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    {/* Select Checkbox */}
                    <td style={{ padding: '14px 14px', textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedLogins.includes(acc.login)}
                        onChange={() => handleToggleSelect(acc.login)}
                        style={{ cursor: 'pointer', width: '15px', height: '15px', accentColor: 'var(--accent-indigo)' }}
                      />
                    </td>

                    {/* Account */}
                    <td style={{ padding: '14px 16px' }}>
                      <div className="font-mono" style={{ fontWeight: '700', color: '#ffffff', fontSize: '0.92rem' }}>
                        {acc.login}
                      </div>
                      {acc.name && acc.name.trim() !== '' && acc.name !== 'MT5 Terminal' && (
                        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                          {acc.name}
                        </div>
                      )}
                    </td>

                    {/* Server */}
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ fontWeight: '500', color: 'var(--text-main)' }}>{acc.server}</div>
                      {acc.broker_name && acc.broker_name !== acc.server && (
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{acc.broker_name}</div>
                      )}
                    </td>

                    {/* Assigned Hardware */}
                    <td style={{ padding: '14px 16px' }}>
                      {acc.assigned_node_id ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span className="badge badge-node font-mono" style={{ fontSize: '0.72rem' }}>
                            {acc.assigned_node_id}
                          </span>
                        </div>
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: 'var(--accent-amber)' }}>
                          Auto-assigning...
                        </span>
                      )}
                    </td>

                    {/* Status */}
                    <td style={{ padding: '14px 16px' }}>
                      {isStopped ? (
                        <span className="badge badge-stopped">
                          <span className="dot-pulse" style={{ background: '#64748b' }}></span>
                          STOPPED
                        </span>
                      ) : isConn ? (
                        <span className="badge badge-connected">
                          <span className="dot-pulse dot-connected"></span>
                          ONLINE ({acc.ping || 0}ms)
                        </span>
                      ) : (
                        <span className="badge badge-starting">
                          <span className="dot-pulse dot-starting"></span>
                          CONNECTING
                        </span>
                      )}
                    </td>

                    {/* Balance */}
                    <td style={{ padding: '14px 16px' }} className="font-mono">
                      ${(acc.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>

                    {/* Equity */}
                    <td style={{ padding: '14px 16px', fontWeight: '600', color: 'var(--accent-cyan)' }} className="font-mono">
                      ${(acc.equity || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>

                    {/* Floating & Closed P/L */}
                    <td style={{ padding: '14px 16px' }} className="font-mono">
                      <span style={{
                        color: isProfitPos ? '#34d399' : '#fb7185',
                        fontWeight: '700',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '2px'
                      }}>
                        {isProfitPos ? '+' : ''}${profit.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                      {acc.daily_closed_pnl !== undefined && Number(acc.daily_closed_pnl) !== 0 && (
                        <div style={{ fontSize: '0.7rem', color: Number(acc.daily_closed_pnl || 0) >= 0 ? '#34d399' : '#fb7185', opacity: 0.85, marginTop: '2px' }}>
                          Day: {Number(acc.daily_closed_pnl || 0) < 0 ? '-' : Number(acc.daily_closed_pnl || 0) > 0 ? '+' : ''}${Math.abs(Number(acc.daily_closed_pnl || 0)).toFixed(2)}
                        </div>
                      )}
                    </td>

                    {/* Free Margin */}
                    <td style={{ padding: '14px 16px', color: 'var(--text-muted)' }} className="font-mono">
                      ${(acc.margin_free || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>

                    {/* Open & Pending Orders Badges */}
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        <button
                          onClick={() => onSelectAccount(acc)}
                          style={{
                            background: (acc.open_positions_count || 0) > 0 ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255, 255, 255, 0.04)',
                            border: (acc.open_positions_count || 0) > 0 ? '1px solid rgba(99, 102, 241, 0.35)' : '1px solid var(--border-subtle)',
                            borderRadius: 'var(--radius-sm)',
                            color: (acc.open_positions_count || 0) > 0 ? '#c7d2fe' : 'var(--text-dim)',
                            padding: '4px 8px',
                            fontSize: '0.75rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            transition: 'all 0.15s ease'
                          }}
                        >
                          <Layers size={12} />
                          <span>{acc.open_positions_count || 0} Open</span>
                        </button>

                        {(acc.pending_orders_count || 0) > 0 && (
                          <button
                            onClick={() => onSelectAccount(acc)}
                            style={{
                              background: 'rgba(245, 158, 11, 0.15)',
                              border: '1px solid rgba(245, 158, 11, 0.35)',
                              borderRadius: 'var(--radius-sm)',
                              color: '#fbbf24',
                              padding: '4px 8px',
                              fontSize: '0.75rem',
                              fontWeight: '600',
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '5px',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            <Clock size={12} />
                            <span>{acc.pending_orders_count} Pending</span>
                          </button>
                        )}
                      </div>
                    </td>

                    {/* Actions */}
                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px' }}>
                        {isStopped ? (
                          <button
                            id={`btn-start-${acc.login}`}
                            className="btn btn-secondary btn-icon"
                            style={{ color: '#34d399' }}
                            title="Start Terminal"
                            onClick={() => onStart(acc.login)}
                          >
                            <Play size={13} fill="#34d399" />
                          </button>
                        ) : (
                          <button
                            id={`btn-stop-${acc.login}`}
                            className="btn btn-secondary btn-icon"
                            style={{ color: '#fb7185' }}
                            title="Stop Terminal"
                            onClick={() => onStop(acc.login)}
                          >
                            <Square size={13} fill="#fb7185" />
                          </button>
                        )}

                        <button
                          id={`btn-restart-${acc.login}`}
                          className="btn btn-secondary btn-icon"
                          style={{ color: 'var(--accent-cyan)' }}
                          title="Restart Terminal"
                          onClick={() => onRestart(acc.login)}
                        >
                          <RotateCw size={13} />
                        </button>

                        <button
                          id={`btn-view-${acc.login}`}
                          className="btn btn-secondary btn-icon"
                          title="View Positions & Telemetry"
                          onClick={() => onSelectAccount(acc)}
                        >
                          <ExternalLink size={13} />
                        </button>

                        <button
                          id={`btn-delete-${acc.login}`}
                          className="btn btn-secondary btn-icon"
                          style={{ color: 'var(--text-muted)' }}
                          title="Delete Account"
                          onClick={() => {
                            if (window.confirm(`Delete MT5 Account ${acc.login}? This stops the terminal and removes it.`)) {
                              onDelete(acc.login);
                            }
                          }}
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
