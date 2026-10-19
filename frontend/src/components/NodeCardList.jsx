import React from 'react';
import { HardDrive, Cpu, Layers, Trash2, Globe, Activity, PlusCircle, CheckCircle2, AlertCircle } from 'lucide-react';

export default function NodeCardList({ nodes, onAddNode, onDeleteNode, onFilterByNode }) {
  return (
    <div style={{ marginBottom: '28px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: '700', letterSpacing: '-0.01em', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <HardDrive size={18} color="var(--accent-cyan)" />
            Distributed Worker Managers (Hardware Cluster)
          </h2>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Each node manages isolated portable MT5 terminals on dedicated VPS or physical machines.
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={onAddNode}
          style={{ fontSize: '0.8rem', padding: '6px 14px', borderColor: 'rgba(0, 242, 254, 0.3)' }}
        >
          <PlusCircle size={14} color="var(--accent-cyan)" />
          <span>+ Add Worker Manager</span>
        </button>
      </div>

      {/* Grid of Nodes */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: '16px'
      }}>
        {nodes.map((node) => {
          const isOnline = node.status === 'online';
          const maxTerminals = node.max_terminals || 25;
          const activeTerminals = node.active_terminals || 0;
          const terminalPct = Math.round((activeTerminals / (maxTerminals || 1)) * 100);

          const cpu = Math.round(node.cpu_percent || 0);
          const ram = Math.round(node.ram_percent || 0);
          const ramUsed = (node.ram_used_mb / 1024).toFixed(1);
          const ramTotal = (node.ram_total_mb / 1024).toFixed(1);

          return (
            <div key={node.node_id} className="glass-card" style={{ padding: '18px', position: 'relative' }}>
              {/* Header */}
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: '700' }}>{node.name}</h3>
                    <span className={`badge ${isOnline ? 'badge-connected' : 'badge-disconnected'}`}>
                      <span className={`dot-pulse ${isOnline ? 'dot-connected' : 'dot-disconnected'}`}></span>
                      {isOnline ? 'ONLINE' : 'OFFLINE'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                    <span className="badge badge-node font-mono">{node.node_id}</span>
                    {node.ip_address && (
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Globe size={11} /> {node.ip_address}
                      </span>
                    )}
                  </div>
                </div>

                {/* Delete Node button (only if not default local-node-1 or user confirms) */}
                <button
                  className="btn btn-secondary btn-icon"
                  style={{ width: '28px', height: '28px', color: '#F43F5E' }}
                  title="Remove this hardware node"
                  onClick={() => {
                    if (window.confirm(`Deregister hardware node '${node.name}' (${node.node_id})? Any running accounts will be auto-reassigned to other online nodes.`)) {
                      onDeleteNode(node.node_id);
                    }
                  }}
                >
                  <Trash2 size={13} />
                </button>
              </div>

              {/* OS & Hardware spec */}
              {node.os_info && (
                <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', marginBottom: '14px', background: 'rgba(255, 255, 255, 0.02)', padding: '6px 10px', borderRadius: '6px' }}>
                  {node.os_info}
                </div>
              )}

              {/* Metrics (CPU, RAM, Terminal slots) */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {/* Terminals Capacity Bar */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <Layers size={13} color="var(--accent-purple)" /> Active Terminals:
                    </span>
                    <span className="font-mono" style={{ fontWeight: '700', color: 'var(--text-main)' }}>
                      {activeTerminals} / {maxTerminals} ({terminalPct}%)
                    </span>
                  </div>
                  <div style={{ width: '100%', height: '6px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{
                      width: `${terminalPct}%`,
                      height: '100%',
                      background: terminalPct > 80 ? 'linear-gradient(90deg, #F59E0B, #F43F5E)' : 'linear-gradient(90deg, #8B5CF6, #00F2FE)',
                      borderRadius: '3px',
                      transition: 'width 0.4s ease'
                    }}></div>
                  </div>
                </div>

                {/* CPU Bar */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <Cpu size={13} color="var(--accent-cyan)" /> Hardware CPU:
                    </span>
                    <span className="font-mono" style={{ fontWeight: '600', color: cpu > 80 ? '#F43F5E' : 'var(--text-main)' }}>
                      {cpu}%
                    </span>
                  </div>
                  <div style={{ width: '100%', height: '5px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{
                      width: `${Math.min(100, cpu)}%`,
                      height: '100%',
                      background: cpu > 80 ? '#F43F5E' : cpu > 60 ? '#F59E0B' : '#00F2FE',
                      borderRadius: '3px'
                    }}></div>
                  </div>
                </div>

                {/* RAM Bar */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <Activity size={13} color="var(--accent-emerald)" /> Hardware RAM:
                    </span>
                    <span className="font-mono" style={{ fontWeight: '600', color: ram > 85 ? '#F43F5E' : 'var(--text-main)' }}>
                      {node.ram_total_mb > 0 ? `${ramUsed}GB / ${ramTotal}GB (${ram}%)` : `${ram}%`}
                    </span>
                  </div>
                  <div style={{ width: '100%', height: '5px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{
                      width: `${Math.min(100, ram)}%`,
                      height: '100%',
                      background: ram > 85 ? '#F43F5E' : ram > 70 ? '#F59E0B' : '#10B981',
                      borderRadius: '3px'
                    }}></div>
                  </div>
                </div>
              </div>

              {/* Footer action */}
              <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: '0.74rem', padding: '4px 10px' }}
                  onClick={() => onFilterByNode(node.node_id)}
                >
                  Filter Accounts on this Node
                </button>
              </div>
            </div>
          );
        })}

        {/* Add Node Call to Action Card */}
        <div
          className="glass-card"
          onClick={onAddNode}
          style={{
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            borderStyle: 'dashed',
            borderColor: 'rgba(0, 242, 254, 0.3)',
            minHeight: '200px',
            background: 'rgba(0, 242, 254, 0.02)'
          }}
        >
          <div style={{
            width: '46px',
            height: '46px',
            borderRadius: '50%',
            background: 'rgba(0, 242, 254, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '12px'
          }}>
            <PlusCircle size={24} color="var(--accent-cyan)" />
          </div>
          <h4 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '4px' }}>Scale with New Hardware</h4>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'center', maxWidth: '240px' }}>
            Add another Windows VPS or local PC to spin up more terminal capacity automatically.
          </p>
        </div>
      </div>
    </div>
  );
}
