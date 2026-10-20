import React, { useState } from 'react';
import { X, Terminal, RefreshCw } from 'lucide-react';

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
      background: 'var(--bg-glass-heavy)',
      backdropFilter: 'blur(20px)',
      borderLeft: '1px solid var(--border-subtle)',
      boxShadow: 'var(--shadow-lg)',
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
          <Terminal size={17} color="var(--accent-indigo)" />
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
      <div style={{ display: 'flex', gap: '6px', padding: '10px 20px', borderBottom: '1px solid var(--border-subtle)', background: 'rgba(0, 0, 0, 0.2)' }}>
        {['ALL', 'INFO', 'WARNING', 'ERROR'].map(lvl => {
          const isActive = levelFilter === lvl;
          return (
            <button
              key={lvl}
              onClick={() => setLevelFilter(lvl)}
              style={{
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                border: isActive ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
                fontSize: '0.72rem',
                fontWeight: '700',
                cursor: 'pointer',
                background: isActive ? 'linear-gradient(90deg, rgba(99, 102, 241, 0.25), rgba(6, 182, 212, 0.12))' : 'rgba(255, 255, 255, 0.03)',
                color: isActive ? '#ffffff' : 'var(--text-secondary)',
                transition: 'all 0.15s ease'
              }}
            >
              {lvl}
            </button>
          );
        })}
      </div>

      {/* Log Feed */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {filteredLogs.length === 0 ? (
          <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
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
                  background: isErr ? 'rgba(244, 63, 94, 0.08)' : isWarn ? 'rgba(245, 158, 11, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                  borderLeft: `3px solid ${isErr ? 'var(--ruby-500)' : isWarn ? 'var(--amber-500)' : 'var(--accent-indigo)'}`,
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.76rem',
                  borderTop: '1px solid var(--border-subtle)',
                  borderRight: '1px solid var(--border-subtle)',
                  borderBottom: '1px solid var(--border-subtle)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '3px' }}>
                  <span style={{
                    fontWeight: '700',
                    color: isErr ? '#fb7185' : isWarn ? '#fbbf24' : '#a5b4fc',
                    fontSize: '0.7rem'
                  }}>
                    [{l.source}] {l.level}
                  </span>
                  <span className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
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
