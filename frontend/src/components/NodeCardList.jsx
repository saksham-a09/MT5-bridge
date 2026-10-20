import React, { useState } from 'react';
import { HardDrive, Trash2, Globe, ChevronDown, ChevronUp } from 'lucide-react';

export default function NodeCardList({ nodes, onAddNode, onDeleteNode, onFilterByNode }) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (!nodes || nodes.length === 0) return null;

  return (
    <div style={{ marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-main)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.92rem',
            fontWeight: '700',
            cursor: 'pointer',
            padding: 0
          }}
        >
          <HardDrive size={16} color="var(--accent-cyan)" />
          <span>Hardware Nodes ({nodes.length})</span>
          {isCollapsed ? <ChevronDown size={14} color="var(--text-muted)" /> : <ChevronUp size={14} color="var(--text-muted)" />}
        </button>

        <button
          className="btn btn-secondary btn-sm"
          onClick={onAddNode}
          style={{ fontSize: '0.75rem', padding: '4px 10px', borderColor: 'rgba(99, 102, 241, 0.35)', color: '#c7d2fe' }}
        >
          <span>+ Add Node</span>
        </button>
      </div>

      {/* Compact Nodes List */}
      {!isCollapsed && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: '12px'
        }}>
          {nodes.map((node) => {
            const isOnline = node.status === 'online';
            const maxTerminals = node.max_terminals || 25;
            const activeTerminals = node.active_terminals || 0;
            const cpu = Math.round(node.cpu_percent || 0);
            const ram = Math.round(node.ram_percent || 0);

            return (
              <div
                key={node.node_id}
                className="glass-card"
                style={{
                  padding: '12px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  borderRadius: 'var(--radius-md)'
                }}
              >
                {/* Header Row */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className={`status-dot ${isOnline ? '' : 'offline'}`} style={{ width: '7px', height: '7px' }}></span>
                    <span style={{ fontSize: '0.88rem', fontWeight: '700', color: '#ffffff' }}>
                      {node.name}
                    </span>
                    <span className="badge badge-node font-mono" style={{ fontSize: '0.68rem', padding: '1px 5px' }}>
                      {node.node_id}
                    </span>
                  </div>

                  <button
                    className="btn btn-secondary btn-icon"
                    style={{ width: '24px', height: '24px', color: 'var(--ruby-500)', border: 'none', background: 'transparent' }}
                    title="Deregister node"
                    onClick={() => {
                      if (window.confirm(`Deregister hardware node '${node.name}' (${node.node_id})?`)) {
                        onDeleteNode(node.node_id);
                      }
                    }}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>

                {/* Info & Metrics Line */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '0.74rem',
                  color: 'var(--text-muted)',
                  borderTop: '1px solid var(--border-subtle)',
                  paddingTop: '6px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {node.ip_address && (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                        <Globe size={11} /> {node.ip_address}
                      </span>
                    )}
                    <span>
                      Terminals: <strong className="font-mono" style={{ color: 'var(--text-main)' }}>{activeTerminals}/{maxTerminals}</strong>
                    </span>
                    <span>
                      CPU: <strong className="font-mono" style={{ color: cpu > 80 ? '#fb7185' : 'var(--text-main)' }}>{cpu}%</strong>
                    </span>
                    <span>
                      RAM: <strong className="font-mono" style={{ color: ram > 85 ? '#fb7185' : 'var(--text-main)' }}>{ram}%</strong>
                    </span>
                  </div>

                  <button
                    onClick={() => onFilterByNode(node.node_id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--accent-cyan)',
                      fontSize: '0.72rem',
                      fontWeight: '600',
                      cursor: 'pointer',
                      padding: 0
                    }}
                  >
                    Filter
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
