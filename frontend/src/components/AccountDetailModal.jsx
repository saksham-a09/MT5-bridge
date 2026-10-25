import React, { useState } from 'react';
import { X, Layers, History, Terminal, Clock, XCircle, Loader2 } from 'lucide-react';
import { closePosition, closeAllPositions, cancelPendingOrder, cancelAllPendingOrders } from '../services/api';

export default function AccountDetailModal({ account, onClose, onRefresh }) {
  const [activeTab, setActiveTab] = useState('positions');
  const [actionLoading, setActionLoading] = useState({});
  const [actionNotice, setActionNotice] = useState(null);

  if (!account) return null;

  const positions = account.open_positions || [];
  const pendingOrders = account.pending_orders || [];
  const deals = account.deals_history || [];
  const isConn = Boolean(account.is_connected);
  const profit = account.profit || 0;
  const isProfitPos = profit >= 0;

  const handleClosePosition = async (ticket, symbol) => {
    if (!window.confirm(`Close position #${ticket} (${symbol}) on Account ${account.login}?`)) return;
    setActionLoading(prev => ({ ...prev, [ticket]: true }));
    setActionNotice(null);
    try {
      const res = await closePosition(account.login, ticket);
      if (!res.success) throw new Error(res.message || 'Failed to close position');
      setActionNotice({ type: 'success', text: `Close signal dispatched for Position #${ticket} (${symbol}).` });
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionNotice({ type: 'error', text: err.message || 'Error closing position' });
    } finally {
      setActionLoading(prev => ({ ...prev, [ticket]: false }));
    }
  };

  const handleCloseAllPositions = async () => {
    if (!window.confirm(`EMERGENCY: Close ALL ${positions.length} open position(s) on Account ${account.login}?`)) return;
    setActionLoading(prev => ({ ...prev, all_positions: true }));
    setActionNotice(null);
    try {
      const res = await closeAllPositions(account.login);
      if (!res.success) throw new Error(res.message || 'Failed to close all positions');
      setActionNotice({ type: 'success', text: `Close-all signal dispatched for Account ${account.login}.` });
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionNotice({ type: 'error', text: err.message || 'Error closing positions' });
    } finally {
      setActionLoading(prev => ({ ...prev, all_positions: false }));
    }
  };

  const handleCancelOrder = async (ticket, symbol) => {
    if (!window.confirm(`Cancel pending order #${ticket} (${symbol}) on Account ${account.login}?`)) return;
    setActionLoading(prev => ({ ...prev, [ticket]: true }));
    setActionNotice(null);
    try {
      const res = await cancelPendingOrder(account.login, ticket);
      if (!res.success) throw new Error(res.message || 'Failed to cancel order');
      setActionNotice({ type: 'success', text: `Cancel signal dispatched for Order #${ticket}.` });
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionNotice({ type: 'error', text: err.message || 'Error canceling order' });
    } finally {
      setActionLoading(prev => ({ ...prev, [ticket]: false }));
    }
  };

  const handleCancelAllOrders = async () => {
    if (!window.confirm(`Cancel ALL ${pendingOrders.length} pending order(s) on Account ${account.login}?`)) return;
    setActionLoading(prev => ({ ...prev, all_orders: true }));
    setActionNotice(null);
    try {
      const res = await cancelAllPendingOrders(account.login);
      if (!res.success) throw new Error(res.message || 'Failed to cancel all orders');
      setActionNotice({ type: 'success', text: `Cancel-all signal dispatched for Account ${account.login}.` });
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionNotice({ type: 'error', text: err.message || 'Error canceling orders' });
    } finally {
      setActionLoading(prev => ({ ...prev, all_orders: false }));
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '820px' }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: '800' }}>
                Account <span className="font-mono gradient-text-accent">{account.login}</span>
              </h3>
              <span className={`badge ${isConn ? 'badge-connected' : 'badge-disconnected'}`}>
                <span className={`dot-pulse ${isConn ? 'dot-connected' : 'dot-disconnected'}`}></span>
                {isConn ? 'ONLINE' : 'DISCONNECTED'}
              </span>
              {account.assigned_node_id && (
                <span className="badge badge-node font-mono">
                  Node: {account.assigned_node_id}
                </span>
              )}
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {account.name && account.name !== 'MT5 Terminal' ? `${account.name} • ` : ''}{account.server}{account.broker_name && account.broker_name !== account.server ? ` (${account.broker_name})` : ''}
            </p>
          </div>

          <button
            onClick={onClose}
            className="btn btn-secondary btn-icon"
            style={{ borderRadius: '50%' }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Quick Stats Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '12px',
          padding: '20px 24px',
          background: 'rgba(0, 0, 0, 0.25)'
        }}>
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Balance</span>
            <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: '700', marginTop: '4px', color: '#ffffff' }}>
              ${(account.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>

          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Equity</span>
            <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: '700', color: 'var(--accent-cyan)', marginTop: '4px' }}>
              ${(account.equity || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>

          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Floating & Closed P/L</span>
            <div className="font-mono" style={{
              fontSize: '1.2rem',
              fontWeight: '700',
              color: isProfitPos ? '#34d399' : '#fb7185',
              marginTop: '4px'
            }}>
              {isProfitPos ? '+' : ''}${profit.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: '0.7rem', color: Number(account.daily_closed_pnl || 0) >= 0 ? '#34d399' : '#fb7185', marginTop: '2px' }}>
              Day Closed: {Number(account.daily_closed_pnl || 0) < 0 ? '-' : Number(account.daily_closed_pnl || 0) > 0 ? '+' : ''}${Math.abs(Number(account.daily_closed_pnl || 0)).toFixed(2)}
            </div>
          </div>

          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Leverage & Margin</span>
            <div className="font-mono" style={{ fontSize: '1.1rem', fontWeight: '700', marginTop: '4px', color: '#ffffff' }}>
              1:{account.leverage || 100}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Free: ${(account.margin_free || 0).toFixed(0)}
            </div>
          </div>
        </div>

        {/* Tab Selection */}
        <div style={{
          display: 'flex',
          padding: '0 24px',
          borderBottom: '1px solid var(--border-subtle)',
          gap: '24px'
        }}>
          {[
            { id: 'positions', label: `Open Positions (${positions.length})`, icon: Layers },
            { id: 'pending', label: `Pending Orders (${pendingOrders.length})`, icon: Clock },
            { id: 'history', label: `Recent Deals (${deals.length})`, icon: History },
            { id: 'terminal', label: 'Terminal Info', icon: Terminal }
          ].map(tab => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '12px 0',
                  background: 'none',
                  border: 'none',
                  borderBottom: active ? '2px solid var(--accent-indigo)' : '2px solid transparent',
                  color: active ? '#ffffff' : 'var(--text-secondary)',
                  fontWeight: '600',
                  fontSize: '0.86rem',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <Icon size={15} color={active ? 'var(--accent-indigo)' : 'currentColor'} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Action Notice Notification Banner */}
        {actionNotice && (
          <div style={{
            margin: '14px 24px 0',
            padding: '10px 14px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.82rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: actionNotice.type === 'error' ? 'rgba(244, 63, 94, 0.15)' : 'rgba(16, 185, 129, 0.15)',
            border: actionNotice.type === 'error' ? '1px solid rgba(244, 63, 94, 0.35)' : '1px solid rgba(16, 185, 129, 0.35)',
            color: actionNotice.type === 'error' ? '#fb7185' : '#34d399'
          }}>
            <span>{actionNotice.text}</span>
            <button
              onClick={() => setActionNotice(null)}
              style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '1rem', lineHeight: 1, padding: '0 4px' }}
            >
              ×
            </button>
          </div>
        )}

        {/* Tab Body */}
        <div style={{ padding: '20px 24px' }}>
          {activeTab === 'positions' && (
            <div>
              {positions.length === 0 ? (
                <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No open orders on this terminal.
                </div>
              ) : (
                <div>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '14px',
                    paddingBottom: '10px',
                    borderBottom: '1px solid var(--border-subtle)'
                  }}>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: '600' }}>
                      {positions.length} Active Market Position{positions.length > 1 ? 's' : ''}
                    </span>
                    <button
                      onClick={handleCloseAllPositions}
                      disabled={actionLoading.all_positions}
                      className="btn btn-sm"
                      style={{
                        background: 'rgba(244, 63, 94, 0.15)',
                        border: '1px solid rgba(244, 63, 94, 0.4)',
                        color: '#fb7185',
                        padding: '5px 12px',
                        fontSize: '0.78rem',
                        fontWeight: '700',
                        borderRadius: 'var(--radius-sm)',
                        cursor: actionLoading.all_positions ? 'not-allowed' : 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                      title="Emergency Close All Open Positions on this Account"
                    >
                      {actionLoading.all_positions ? (
                        <>
                          <Loader2 size={13} className="animate-spin" />
                          <span>Closing All...</span>
                        </>
                      ) : (
                        <>
                          <XCircle size={13} />
                          <span>Close All Positions</span>
                        </>
                      )}
                    </button>
                  </div>

                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                      <thead>
                        <tr style={{ color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.04em' }}>
                          <th style={{ padding: '8px 10px' }}>Ticket</th>
                          <th style={{ padding: '8px 10px' }}>Symbol</th>
                          <th style={{ padding: '8px 10px' }}>Type</th>
                          <th style={{ padding: '8px 10px' }}>Volume</th>
                          <th style={{ padding: '8px 10px' }}>Open Price</th>
                          <th style={{ padding: '8px 10px' }}>Current</th>
                          <th style={{ padding: '8px 10px' }}>S/L - T/P</th>
                          <th style={{ padding: '8px 10px', textAlign: 'right' }}>Profit ($)</th>
                          <th style={{ padding: '8px 10px', textAlign: 'center', width: '90px' }}>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {positions.map(p => {
                          const isBuy = p.type === 'BUY';
                          const posProfit = p.profit || 0;
                          const isPosProfit = posProfit >= 0;
                          const isClosing = Boolean(actionLoading[p.ticket]);
                          return (
                            <tr key={p.ticket} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.03)' }}>
                              <td className="font-mono" style={{ padding: '10px', color: 'var(--text-muted)' }}>#{p.ticket}</td>
                              <td className="font-mono" style={{ padding: '10px', fontWeight: '700', color: '#ffffff' }}>{p.symbol}</td>
                              <td style={{ padding: '10px' }}>
                                <span style={{
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  fontSize: '0.72rem',
                                  fontWeight: '700',
                                  background: isBuy ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                                  color: isBuy ? '#34d399' : '#fb7185',
                                  border: isBuy ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(244, 63, 94, 0.3)'
                                }}>
                                  {p.type}
                                </span>
                              </td>
                              <td className="font-mono" style={{ padding: '10px' }}>{p.volume}</td>
                              <td className="font-mono" style={{ padding: '10px' }}>{p.price_open}</td>
                              <td className="font-mono" style={{ padding: '10px' }}>{p.price_current}</td>
                              <td className="font-mono" style={{ padding: '10px', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                                {p.sl || '-'} / {p.tp || '-'}
                              </td>
                              <td className="font-mono" style={{
                                padding: '10px',
                                textAlign: 'right',
                                fontWeight: '700',
                                color: isPosProfit ? '#34d399' : '#fb7185'
                              }}>
                                {isPosProfit ? '+' : ''}${posProfit.toFixed(2)}
                              </td>
                              <td style={{ padding: '10px', textAlign: 'center' }}>
                                <button
                                  onClick={() => handleClosePosition(p.ticket, p.symbol)}
                                  disabled={isClosing}
                                  className="btn btn-sm"
                                  style={{
                                    padding: '3px 8px',
                                    fontSize: '0.72rem',
                                    fontWeight: '700',
                                    background: 'rgba(244, 63, 94, 0.12)',
                                    color: '#fb7185',
                                    border: '1px solid rgba(244, 63, 94, 0.35)',
                                    borderRadius: 'var(--radius-sm)',
                                    cursor: isClosing ? 'not-allowed' : 'pointer',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                    transition: 'all 0.15s ease'
                                  }}
                                  title={`Close Position #${p.ticket}`}
                                >
                                  {isClosing ? (
                                    <>
                                      <Loader2 size={11} className="animate-spin" />
                                      <span>Closing...</span>
                                    </>
                                  ) : (
                                    <span>Close</span>
                                  )}
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'pending' && (
            <div>
              {pendingOrders.length === 0 ? (
                <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No pending orders on this terminal.
                </div>
              ) : (
                <div>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '14px',
                    paddingBottom: '10px',
                    borderBottom: '1px solid var(--border-subtle)'
                  }}>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: '600' }}>
                      {pendingOrders.length} Pending Order{pendingOrders.length > 1 ? 's' : ''}
                    </span>
                    <button
                      onClick={handleCancelAllOrders}
                      disabled={actionLoading.all_orders}
                      className="btn btn-sm"
                      style={{
                        background: 'rgba(245, 158, 11, 0.15)',
                        border: '1px solid rgba(245, 158, 11, 0.4)',
                        color: '#fbbf24',
                        padding: '5px 12px',
                        fontSize: '0.78rem',
                        fontWeight: '700',
                        borderRadius: 'var(--radius-sm)',
                        cursor: actionLoading.all_orders ? 'not-allowed' : 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                      title="Cancel All Pending Orders on this Account"
                    >
                      {actionLoading.all_orders ? (
                        <>
                          <Loader2 size={13} className="animate-spin" />
                          <span>Canceling All...</span>
                        </>
                      ) : (
                        <>
                          <Clock size={13} />
                          <span>Cancel All Orders</span>
                        </>
                      )}
                    </button>
                  </div>

                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                      <thead>
                        <tr style={{ color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.04em' }}>
                          <th style={{ padding: '8px 10px' }}>Ticket</th>
                          <th style={{ padding: '8px 10px' }}>Symbol</th>
                          <th style={{ padding: '8px 10px' }}>Type</th>
                          <th style={{ padding: '8px 10px' }}>Volume</th>
                          <th style={{ padding: '8px 10px' }}>Trigger Price</th>
                          <th style={{ padding: '8px 10px' }}>Current</th>
                          <th style={{ padding: '8px 10px' }}>S/L - T/P</th>
                          <th style={{ padding: '8px 10px' }}>Comment</th>
                          <th style={{ padding: '8px 10px', textAlign: 'center', width: '90px' }}>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pendingOrders.map(o => {
                          const isBuy = String(o.type).includes('BUY');
                          const isCanceling = Boolean(actionLoading[o.ticket]);
                          return (
                            <tr key={o.ticket} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.03)' }}>
                              <td className="font-mono" style={{ padding: '10px', color: 'var(--text-muted)' }}>#{o.ticket}</td>
                              <td className="font-mono" style={{ padding: '10px', fontWeight: '700', color: '#ffffff' }}>{o.symbol}</td>
                              <td style={{ padding: '10px' }}>
                                <span style={{
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  fontSize: '0.72rem',
                                  fontWeight: '700',
                                  background: isBuy ? 'rgba(99, 102, 241, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                                  color: isBuy ? '#c7d2fe' : '#fb7185',
                                  border: isBuy ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid rgba(244, 63, 94, 0.3)'
                                }}>
                                  {o.type}
                                </span>
                              </td>
                              <td className="font-mono" style={{ padding: '10px' }}>{o.volume}</td>
                              <td className="font-mono" style={{ padding: '10px', fontWeight: '600' }}>{o.price_open}</td>
                              <td className="font-mono" style={{ padding: '10px' }}>{o.price_current || '-'}</td>
                              <td className="font-mono" style={{ padding: '10px', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                                {o.sl || '-'} / {o.tp || '-'}
                              </td>
                              <td className="font-mono" style={{ padding: '10px', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                                {o.comment || '-'}
                              </td>
                              <td style={{ padding: '10px', textAlign: 'center' }}>
                                <button
                                  onClick={() => handleCancelOrder(o.ticket, o.symbol)}
                                  disabled={isCanceling}
                                  className="btn btn-sm"
                                  style={{
                                    padding: '3px 8px',
                                    fontSize: '0.72rem',
                                    fontWeight: '700',
                                    background: 'rgba(245, 158, 11, 0.12)',
                                    color: '#fbbf24',
                                    border: '1px solid rgba(245, 158, 11, 0.35)',
                                    borderRadius: 'var(--radius-sm)',
                                    cursor: isCanceling ? 'not-allowed' : 'pointer',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                    transition: 'all 0.15s ease'
                                  }}
                                  title={`Cancel Order #${o.ticket}`}
                                >
                                  {isCanceling ? (
                                    <>
                                      <Loader2 size={11} className="animate-spin" />
                                      <span>Canceling...</span>
                                    </>
                                  ) : (
                                    <span>Cancel</span>
                                  )}
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'history' && (
            <div>
              {deals.length === 0 ? (
                <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No recent deal history retrieved.
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                    <thead>
                      <tr style={{ color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.04em' }}>
                        <th style={{ padding: '8px 10px' }}>Deal Ticket</th>
                        <th style={{ padding: '8px 10px' }}>Symbol</th>
                        <th style={{ padding: '8px 10px' }}>Type</th>
                        <th style={{ padding: '8px 10px' }}>Volume</th>
                        <th style={{ padding: '8px 10px' }}>Close Price</th>
                        <th style={{ padding: '8px 10px' }}>Time</th>
                        <th style={{ padding: '8px 10px', textAlign: 'right' }}>Net Profit</th>
                      </tr>
                    </thead>
                    <tbody>
                      {deals.map(d => {
                        const dProfit = d.profit || 0;
                        const isDPProfit = dProfit >= 0;
                        return (
                          <tr key={d.ticket} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.03)' }}>
                            <td className="font-mono" style={{ padding: '10px', color: 'var(--text-muted)' }}>#{d.ticket}</td>
                            <td className="font-mono" style={{ padding: '10px', fontWeight: '700', color: '#ffffff' }}>{d.symbol}</td>
                            <td style={{ padding: '10px' }}>{d.type}</td>
                            <td className="font-mono" style={{ padding: '10px' }}>{d.volume}</td>
                            <td className="font-mono" style={{ padding: '10px' }}>{d.price}</td>
                            <td style={{ padding: '10px', color: 'var(--text-muted)', fontSize: '0.75rem' }}>{d.time}</td>
                            <td className="font-mono" style={{
                              padding: '10px',
                              textAlign: 'right',
                              fontWeight: '700',
                              color: isDPProfit ? '#34d399' : '#fb7185'
                            }}>
                              {isDPProfit ? '+' : ''}${dProfit.toFixed(2)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {activeTab === 'terminal' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.85rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Assigned Hardware Node</span>
                  <div className="font-mono" style={{ fontWeight: '600', marginTop: '2px', color: 'var(--accent-cyan)' }}>
                    {account.assigned_node_id || 'Auto-balancing'}
                  </div>
                </div>
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Target Node Pin</span>
                  <div className="font-mono" style={{ fontWeight: '600', marginTop: '2px', color: '#ffffff' }}>
                    {account.target_node_id || 'auto'}
                  </div>
                </div>
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Attached Expert Advisor</span>
                  <div style={{ fontWeight: '600', marginTop: '2px', color: '#ffffff' }}>
                    {account.expert || 'None (Standard Execution)'}
                  </div>
                </div>
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Symbol / Timeframe</span>
                  <div className="font-mono" style={{ fontWeight: '600', marginTop: '2px', color: '#ffffff' }}>
                    {account.symbol || 'XAUUSD'} ({account.timeframe || 'M1'})
                  </div>
                </div>
              </div>

              {account.error_message && (
                <div style={{
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'rgba(244, 63, 94, 0.1)',
                  border: '1px solid rgba(244, 63, 94, 0.3)',
                  color: '#fb7185',
                  fontSize: '0.8rem'
                }}>
                  <strong>Terminal Diagnostic Note:</strong> {account.error_message}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'flex-end',
          background: 'rgba(0, 0, 0, 0.15)'
        }}>
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
