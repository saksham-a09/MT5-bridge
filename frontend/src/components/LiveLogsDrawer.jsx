import React, { useState } from 'react';
import { X, Terminal, AlertTriangle, Info, AlertCircle, RefreshCw } from 'lucide-react';

export default function LiveLogsDrawer({ isOpen, onClose, logs, onRefresh }) {
  const [levelFilter, setLevelFilter] = useState('ALL');

  if (!isOpen) return null;

  const filteredLogs = logs.filter(log => {
    if (levelFilter === 'ALL') return true;
    return log.level === levelFilter;
  });

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      right: 0,
      bottom: 0,
      width: '460px',
      maxWidth: '100vw',
      background: '#0B101E',
      borderLeft: '1px solid var(--border-hover)',
      boxShadow: '-10px 0 40px rgba(0, 0, 0, 0.6)',
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column',
      animation: 'slideInRight 0.25s ease'
    }}>
      {/* Header */}
      <div style={{
        padding: '18px 20px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={17} color="var(--accent-cyan)" />
          <h3 style={{ fontSize: '1rem', fontWeight: '700' }}>Cluster System Logs</h3>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={onRefresh}
            className="btn btn-secondary btn-icon"
            style={{ width: '28px', height: '28px' }}
            title="Refresh logs"
          >
            <RefreshCw size={13} />
          </button>
          <button
            onClick={onClose}
            className="btn btn-secondary btn-icon"
            style={{ width: '28px', height: '28px', borderRadius: '50%' }}
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '6px', padding: '10px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
        {['ALL', 'INFO', 'WARNING', 'ERROR'].map(lvl => (
          <button
            key={lvl}
            onClick={() => setLevelFilter(lvl)}
            style={{
              padding: '4px 10px',
              borderRadius: '4px',
              border: 'none',
              fontSize: '0.72rem',
              fontWeight: '700',
              cursor: 'pointer',
              background: levelFilter === lvl ? 'rgba(0, 242, 254, 0.15)' : 'rgba(255, 255, 255, 0.03)',
              color: levelFilter === lvl ? 'var(--accent-cyan)' : 'var(--text-muted)'
            }}
          >
            {lvl}
          </button>
        ))}
      </div>

      {/* Log Feed */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {filteredLogs.length === 0 ? (
          <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
            No logs found for this filter.
          </div>
        ) : (
          filteredLogs.map(l => {
            const isErr = l.level === 'ERROR';
            const isWarn = l.level === 'WARNING';
            return (
              <div
                key={l.id}
                style={{
                  background: isErr ? 'rgba(244, 63, 94, 0.07)' : isWarn ? 'rgba(245, 158, 11, 0.07)' : 'rgba(255, 255, 255, 0.02)',
                  borderLeft: `3px solid ${isErr ? '#F43F5E' : isWarn ? '#F59E0B' : 'var(--accent-cyan)'}`,
                  padding: '8px 12px',
                  borderRadius: '4px',
                  fontSize: '0.76rem'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '3px' }}>
                  <span style={{
                    fontWeight: '700',
                    color: isErr ? '#FB7185' : isWarn ? '#FBBF24' : 'var(--accent-cyan)',
                    fontSize: '0.7rem'
                  }}>
                    [{l.source}] {l.level}
                  </span>
                  <span className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>
                    {l.created_at ? l.created_at.substring(11, 19) : ''}
                  </span>
                </div>
                <div style={{ color: 'var(--text-main)', lineHeight: '1.4' }}>
                  {l.message}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
