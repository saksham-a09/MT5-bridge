import React from 'react';
import { 
  Play, Square, RotateCw, Trash2, ExternalLink, Search, 
  Filter, CheckCircle2, XCircle, AlertTriangle, Layers, Clock, ArrowUpRight, ArrowDownRight 
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
  onSelectAccount 
}) {
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

  return (
    <div className="glass-card" style={{ padding: '22px' }}>
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
            fontSize: '0.8rem',
            padding: '2px 8px',
            borderRadius: 'var(--radius-full)',
            background: 'rgba(255, 255, 255, 0.08)',
            color: 'var(--text-muted)',
            fontWeight: '600'
          }}>
            {filtered.length} of {accounts.length}
          </span>
          {nodeFilter && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(0, 242, 254, 0.1)', padding: '2px 8px', borderRadius: '4px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>Node: {nodeFilter}</span>
              <button
                onClick={() => setNodeFilter(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontSize: '0.85rem' }}
              >
                ×
              </button>
            </div>
          )}
        </div>

        {/* Search & Status Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Status Pills */}
          <div style={{ display: 'flex', background: 'rgba(0, 0, 0, 0.25)', padding: '3px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            {[
              { id: 'all', label: 'All' },
              { id: 'active', label: 'Active' },
              { id: 'connected', label: 'Connected' },
              { id: 'stopped', label: 'Stopped' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setStatusFilter(tab.id)}
                style={{
                  background: statusFilter === tab.id ? 'rgba(0, 242, 254, 0.18)' : 'transparent',
                  color: statusFilter === tab.id ? 'var(--accent-cyan)' : 'var(--text-muted)',
                  border: 'none',
                  padding: '5px 12px',
                  borderRadius: '6px',
                  fontSize: '0.78rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div style={{ position: 'relative', width: '220px' }}>
            <Search size={15} color="var(--text-dim)" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Search login, server..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field"
              style={{ paddingLeft: '32px', fontSize: '0.8rem', height: '34px' }}
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.86rem' }}>
          <thead>
            <tr style={{
              borderBottom: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
              fontSize: '0.75rem',
              textTransform: 'uppercase',
              letterSpacing: '0.04em'
            }}>
              <th style={{ padding: '12px 14px' }}>Account</th>
              <th style={{ padding: '12px 14px' }}>Broker & Server</th>
              <th style={{ padding: '12px 14px' }}>Assigned Hardware</th>
              <th style={{ padding: '12px 14px' }}>Status</th>
              <th style={{ padding: '12px 14px' }}>Balance</th>
              <th style={{ padding: '12px 14px' }}>Equity</th>
              <th style={{ padding: '12px 14px' }}>Floating P/L</th>
              <th style={{ padding: '12px 14px' }}>Margin Free</th>
              <th style={{ padding: '12px 14px' }}>Open Orders</th>
              <th style={{ padding: '12px 14px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan="10" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No MT5 accounts match the selected criteria.
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
                      borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                      transition: 'background 0.15s ease'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    {/* Account */}
                    <td style={{ padding: '14px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div>
                          <div className="font-mono" style={{ fontWeight: '700', color: 'var(--text-main)', fontSize: '0.92rem' }}>
                            {acc.login}
                          </div>
                          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                            {acc.name || 'MT5 Terminal'}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Server */}
                    <td style={{ padding: '14px' }}>
                      <div style={{ fontWeight: '500', color: 'var(--text-main)' }}>{acc.server}</div>
                      {acc.broker_name && (
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>{acc.broker_name}</div>
                      )}
                    </td>

                    {/* Assigned Hardware */}
                    <td style={{ padding: '14px' }}>
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
                    <td style={{ padding: '14px' }}>
                      {isStopped ? (
                        <span className="badge badge-stopped">
                          <span className="dot-pulse" style={{ background: '#64748B' }}></span>
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
                    <td style={{ padding: '14px' }} className="font-mono">
                      ${(acc.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>

                    {/* Equity */}
                    <td style={{ padding: '14px', fontWeight: '600', color: 'var(--accent-cyan)' }} className="font-mono">
                      ${(acc.equity || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>

                    {/* Floating P/L */}
                    <td style={{ padding: '14px' }} className="font-mono">
                      <span style={{
                        color: isProfitPos ? '#34D399' : '#FB7185',
                        fontWeight: '700',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '2px'
                      }}>
                        {isProfitPos ? '+' : ''}${profit.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </td>

                    {/* Free Margin */}
                    <td style={{ padding: '14px', color: 'var(--text-muted)' }} className="font-mono">
                      ${(acc.margin_free || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>

                    {/* Open & Pending Orders Badges */}
                    <td style={{ padding: '14px' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        <button
                          onClick={() => onSelectAccount(acc)}
                          style={{
                            background: (acc.open_positions_count || 0) > 0 ? 'rgba(0, 242, 254, 0.12)' : 'rgba(255, 255, 255, 0.04)',
                            border: (acc.open_positions_count || 0) > 0 ? '1px solid rgba(0, 242, 254, 0.3)' : '1px solid var(--border-subtle)',
                            borderRadius: '6px',
                            color: (acc.open_positions_count || 0) > 0 ? 'var(--accent-cyan)' : 'var(--text-dim)',
                            padding: '4px 8px',
                            fontSize: '0.76rem',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px'
                          }}
                        >
                          <Layers size={12} />
                          <span>{acc.open_positions_count || 0} Open</span>
                        </button>

                        {(acc.pending_orders_count || 0) > 0 && (
                          <button
                            onClick={() => onSelectAccount(acc)}
                            style={{
                              background: 'rgba(245, 158, 11, 0.12)',
                              border: '1px solid rgba(245, 158, 11, 0.3)',
                              borderRadius: '6px',
                              color: '#FBBF24',
                              padding: '4px 8px',
                              fontSize: '0.76rem',
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '5px'
                            }}
                          >
                            <Clock size={12} />
                            <span>{acc.pending_orders_count} Pending</span>
                          </button>
                        )}
                      </div>
                    </td>

                    {/* Actions */}
                    <td style={{ padding: '14px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px' }}>
                        {isStopped ? (
                          <button
                            id={`btn-start-${acc.login}`}
                            className="btn btn-secondary btn-icon"
                            style={{ color: '#34D399' }}
                            title="Start Terminal"
                            onClick={() => onStart(acc.login)}
                          >
                            <Play size={13} fill="#34D399" />
                          </button>
                        ) : (
                          <button
                            id={`btn-stop-${acc.login}`}
                            className="btn btn-secondary btn-icon"
                            style={{ color: '#F43F5E' }}
                            title="Stop Terminal"
                            onClick={() => onStop(acc.login)}
                          >
                            <Square size={13} fill="#F43F5E" />
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
                          style={{ color: 'var(--text-dim)' }}
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
