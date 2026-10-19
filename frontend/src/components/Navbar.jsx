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
      padding: '16px 28px',
      background: 'rgba(10, 16, 29, 0.85)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid var(--border-subtle)',
      position: 'sticky',
      top: 0,
      zIndex: 100
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          width: '42px',
          height: '42px',
          borderRadius: '12px',
          background: 'linear-gradient(135deg, rgba(0, 242, 254, 0.2), rgba(79, 172, 254, 0.2))',
          border: '1px solid rgba(0, 242, 254, 0.4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 20px rgba(0, 242, 254, 0.25)'
        }}>
          <Server size={22} color="var(--accent-cyan)" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '1.25rem', fontWeight: '800', letterSpacing: '-0.02em' }}>
              MT5 <span className="gradient-text">TERMINAL HUB</span>
            </h1>
            <span style={{
              fontSize: '0.65rem',
              fontWeight: '700',
              padding: '2px 6px',
              borderRadius: '4px',
              background: 'rgba(0, 242, 254, 0.1)',
              color: 'var(--accent-cyan)',
              border: '1px solid rgba(0, 242, 254, 0.25)'
            }}>
              DISTRIBUTED v1.0
            </span>
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Multi-Hardware Scalable MetaTrader 5 Terminal Cluster
          </p>
        </div>
      </div>

      {/* View Switcher: Cluster Overview vs Trade Copier */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        background: 'rgba(255, 255, 255, 0.04)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '10px',
        padding: '4px'
      }}>
        <button
          onClick={() => onSelectView && onSelectView('dashboard')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '7px 16px',
            borderRadius: '8px',
            border: 'none',
            fontSize: '0.85rem',
            fontWeight: '600',
            cursor: 'pointer',
            transition: 'all 0.2s',
            background: currentView === 'dashboard' ? 'rgba(0, 242, 254, 0.15)' : 'transparent',
            color: currentView === 'dashboard' ? 'var(--accent-cyan)' : 'var(--text-muted)',
            boxShadow: currentView === 'dashboard' ? '0 0 12px rgba(0, 242, 254, 0.2)' : 'none'
          }}
        >
          <Activity size={15} />
          <span>Overview</span>
        </button>

        <button
          onClick={() => onSelectView && onSelectView('copier')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '7px 16px',
            borderRadius: '8px',
            border: 'none',
            fontSize: '0.85rem',
            fontWeight: '600',
            cursor: 'pointer',
            transition: 'all 0.2s',
            background: currentView === 'copier' ? 'rgba(245, 158, 11, 0.15)' : 'transparent',
            color: currentView === 'copier' ? 'var(--accent-amber)' : 'var(--text-muted)',
            boxShadow: currentView === 'copier' ? '0 0 12px rgba(245, 158, 11, 0.2)' : 'none'
          }}
        >
          <Zap size={15} />
          <span>Trade Copier</span>
        </button>
      </div>

      {/* Cluster Status Pills */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div className="glass-card" style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '6px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span className={`dot-pulse ${wsConnected ? 'dot-connected' : 'dot-disconnected'}`}></span>
            <span style={{ fontSize: '0.8rem', fontWeight: '600', color: wsConnected ? '#34D399' : '#FB7185' }}>
              {wsConnected ? 'Live Hub Active' : 'Connecting...'}
            </span>
          </div>
          <div style={{ width: '1px', height: '14px', background: 'var(--border-subtle)' }}></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <HardDrive size={14} color="var(--accent-blue)" />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Nodes:</span>
            <span className="font-mono" style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--accent-cyan)' }}>
              {nodesCount}
            </span>
          </div>
          <div style={{ width: '1px', height: '14px', background: 'var(--border-subtle)' }}></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Layers size={14} color="var(--accent-purple)" />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Terminals:</span>
            <span className="font-mono" style={{ fontSize: '0.85rem', fontWeight: '700', color: '#A78BFA' }}>
              {terminalsCount}
            </span>
          </div>
        </div>

        {/* Buttons */}
        <button
          id="btn-add-node"
          className="btn btn-secondary"
          onClick={onAddNode}
          title="Add new worker manager on remote VPS or PC hardware to scale"
          style={{ borderColor: 'rgba(139, 92, 246, 0.4)', color: '#C4B5FD' }}
        >
          <HardDrive size={15} />
          <span>+ Add Hardware Node</span>
        </button>

        <button
          id="btn-add-account"
          className="btn btn-primary"
          onClick={onAddAccount}
        >
          <Plus size={16} />
          <span>+ Add MT5 Account</span>
        </button>

        <button
          id="btn-toggle-logs"
          className="btn btn-secondary btn-icon"
          onClick={onToggleLogs}
          title="View Cluster Event Logs"
        >
          <Terminal size={16} />
        </button>

        <button
          id="btn-refresh"
          className="btn btn-secondary btn-icon"
          onClick={onRefresh}
          title="Refresh Data"
        >
          <RefreshCw size={15} />
        </button>
      </div>
    </header>
  );
}
