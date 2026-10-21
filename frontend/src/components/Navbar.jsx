import React from 'react';
import { Server, Activity, Plus, HardDrive, RefreshCw, Terminal, Layers, Zap } from 'lucide-react';

export default function Navbar({ 
  wsConnected, 
  nodesCount, 
  terminalsCount, 
  currentView = 'dashboard',
  onSelectView,
  onAddAccount, 
  onAddNode, 
  onToggleLogs, 
  onRefresh 
}) {
  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '14px 28px',
      background: 'var(--bg-glass-heavy)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid var(--border-subtle)',
      position: 'sticky',
      top: 0,
      zIndex: 100
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: 'var(--radius-md)',
          background: 'linear-gradient(135deg, var(--accent-indigo), var(--accent-cyan))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#ffffff',
          boxShadow: '0 0 14px rgba(99, 102, 241, 0.35)'
        }}>
          <Server size={20} color="#ffffff" />
        </div>
      </div>

      {/* View Switcher: Cluster Overview vs Trade Copier */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        background: 'rgba(255, 255, 255, 0.04)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: '3px'
      }}>
        <button
          onClick={() => onSelectView && onSelectView('dashboard')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 14px',
            borderRadius: 'var(--radius-sm)',
            border: currentView === 'dashboard' ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
            fontSize: '0.82rem',
            fontWeight: '600',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            background: currentView === 'dashboard' ? 'linear-gradient(90deg, rgba(99, 102, 241, 0.22), rgba(6, 182, 212, 0.1))' : 'transparent',
            color: currentView === 'dashboard' ? '#ffffff' : 'var(--text-secondary)',
            boxShadow: currentView === 'dashboard' ? '0 2px 8px rgba(0, 0, 0, 0.35)' : 'none'
          }}
        >
          <Activity size={14} color={currentView === 'dashboard' ? 'var(--accent-cyan)' : 'currentColor'} />
          <span>Overview</span>
        </button>

        <button
          onClick={() => onSelectView && onSelectView('copier')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 14px',
            borderRadius: 'var(--radius-sm)',
            border: currentView === 'copier' ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid transparent',
            fontSize: '0.82rem',
            fontWeight: '600',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            background: currentView === 'copier' ? 'linear-gradient(90deg, rgba(245, 158, 11, 0.22), rgba(99, 102, 241, 0.12))' : 'transparent',
            color: currentView === 'copier' ? '#fef3c7' : 'var(--text-secondary)',
            boxShadow: currentView === 'copier' ? '0 2px 8px rgba(0, 0, 0, 0.35)' : 'none'
          }}
        >
          <Zap size={14} color={currentView === 'copier' ? 'var(--accent-amber)' : 'currentColor'} />
          <span>Trade Copier</span>
        </button>
      </div>

      {/* Cluster Status & Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div className="glass-card" style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '5px 14px', borderRadius: 'var(--radius-full)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span className={`status-dot ${wsConnected ? '' : 'offline'}`} style={{ width: '7px', height: '7px' }}></span>
            <span style={{ fontSize: '0.76rem', fontWeight: '600', color: wsConnected ? '#34d399' : '#fb7185' }}>
              {wsConnected ? 'Connected' : 'Offline'}
            </span>
          </div>
          <div style={{ width: '1px', height: '12px', background: 'var(--border-subtle)' }}></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <HardDrive size={13} color="var(--accent-cyan)" />
            <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>Nodes:</span>
            <span className="font-mono" style={{ fontSize: '0.82rem', fontWeight: '700', color: '#ffffff' }}>
              {nodesCount}
            </span>
          </div>
          <div style={{ width: '1px', height: '12px', background: 'var(--border-subtle)' }}></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Layers size={13} color="var(--accent-indigo)" />
            <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>Terminals:</span>
            <span className="font-mono" style={{ fontSize: '0.82rem', fontWeight: '700', color: '#c7d2fe' }}>
              {terminalsCount}
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <button
          id="btn-add-node"
          className="btn btn-secondary btn-sm"
          onClick={onAddNode}
          title="Add Hardware Worker Node"
          style={{ borderColor: 'rgba(99, 102, 241, 0.35)', color: '#c7d2fe', padding: '6px 12px' }}
        >
          <HardDrive size={13} />
          <span>+ Node</span>
        </button>

        <button
          id="btn-add-account"
          className="btn btn-primary btn-sm"
          onClick={onAddAccount}
          style={{ padding: '6px 14px' }}
        >
          <Plus size={14} />
          <span>+ Account</span>
        </button>

        <button
          id="btn-toggle-logs"
          className="btn btn-secondary btn-icon"
          onClick={onToggleLogs}
          title="Cluster Logs"
          style={{ width: '32px', height: '32px' }}
        >
          <Terminal size={14} />
        </button>

        <button
          id="btn-refresh"
          className="btn btn-secondary btn-icon"
          onClick={onRefresh}
          title="Refresh Data"
          style={{ width: '32px', height: '32px' }}
        >
          <RefreshCw size={13} />
        </button>
      </div>
    </header>
  );
}
