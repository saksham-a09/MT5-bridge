import React from 'react';
import { Wallet, TrendingUp, Cpu, Server, Activity, ArrowUpRight, ArrowDownRight } from 'lucide-react';

export default function StatsOverview({ summary }) {
  const accounts = summary?.accounts || {};
  const nodes = summary?.nodes || {};

  const totalBalance = accounts.total_balance || 0;
  const totalEquity = accounts.total_equity || 0;
  const totalProfit = accounts.total_profit || 0;
  const isProfitPositive = totalProfit >= 0;

  const totalCapacity = nodes.total_terminal_capacity || 25;
  const activeTerminals = nodes.total_active_terminals || accounts.connected_accounts || 0;
  const capacityPct = Math.min(100, Math.round((activeTerminals / (totalCapacity || 1)) * 100));

  const onlineNodes = nodes.online_nodes || 0;
  const totalNodes = nodes.total_nodes || 0;
  const avgCpu = Math.round(nodes.avg_cpu_percent || 0);
  const avgRam = Math.round(nodes.avg_ram_percent || 0);

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))',
      gap: '16px',
      marginBottom: '24px'
    }}>
      {/* 1. Combined Balance */}
      <div className="glass-card" style={{ padding: '20px', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', top: '-10px', right: '-10px', width: '90px', height: '90px',
          background: 'radial-gradient(circle, rgba(0, 242, 254, 0.12) 0%, transparent 70%)',
          borderRadius: '50%'
        }}></div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <span style={{ fontSize: '0.82rem', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Combined Balance
          </span>
          <div style={{
            width: '32px', height: '32px', borderRadius: '8px',
            background: 'rgba(0, 242, 254, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Wallet size={16} color="var(--accent-cyan)" />
          </div>
        </div>
        <div className="font-mono" style={{ fontSize: '1.75rem', fontWeight: '800', color: 'var(--text-main)', marginBottom: '4px' }}>
          ${totalBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
          Across <span style={{ color: 'var(--text-main)', fontWeight: '600' }}>{accounts.total_accounts || 0}</span> configured accounts
        </div>
      </div>

      {/* 2. Combined Equity */}
      <div className="glass-card" style={{ padding: '20px', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', top: '-10px', right: '-10px', width: '90px', height: '90px',
          background: 'radial-gradient(circle, rgba(79, 172, 254, 0.12) 0%, transparent 70%)',
          borderRadius: '50%'
        }}></div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <span style={{ fontSize: '0.82rem', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Combined Equity
          </span>
          <div style={{
            width: '32px', height: '32px', borderRadius: '8px',
            background: 'rgba(79, 172, 254, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <TrendingUp size={16} color="var(--accent-blue)" />
          </div>
        </div>
        <div className="font-mono" style={{ fontSize: '1.75rem', fontWeight: '800', color: 'var(--accent-cyan)', marginBottom: '4px' }}>
          ${totalEquity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
          Live margin equity valuation
        </div>
      </div>

      {/* 3. Floating P/L */}
      <div className="glass-card" style={{ padding: '20px', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', top: '-10px', right: '-10px', width: '90px', height: '90px',
          background: isProfitPositive 
            ? 'radial-gradient(circle, rgba(16, 185, 129, 0.15) 0%, transparent 70%)'
            : 'radial-gradient(circle, rgba(244, 63, 94, 0.15) 0%, transparent 70%)',
          borderRadius: '50%'
        }}></div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <span style={{ fontSize: '0.82rem', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Floating Profit / Loss
          </span>
          <div style={{
            width: '32px', height: '32px', borderRadius: '8px',
            background: isProfitPositive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            {isProfitPositive ? <ArrowUpRight size={18} color="#10B981" /> : <ArrowDownRight size={18} color="#F43F5E" />}
          </div>
        </div>
        <div className="font-mono" style={{
          fontSize: '1.75rem',
          fontWeight: '800',
          color: isProfitPositive ? '#34D399' : '#FB7185',
          marginBottom: '4px'
        }}>
          {isProfitPositive ? '+' : ''}${totalProfit.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
          Open positions: <span style={{ color: 'var(--text-main)', fontWeight: '600' }}>{accounts.total_open_positions || 0}</span> orders active
        </div>
      </div>

      {/* 4. Terminal Slots & Capacity */}
      <div className="glass-card" style={{ padding: '20px', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', top: '-10px', right: '-10px', width: '90px', height: '90px',
          background: 'radial-gradient(circle, rgba(139, 92, 246, 0.12) 0%, transparent 70%)',
          borderRadius: '50%'
        }}></div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <span style={{ fontSize: '0.82rem', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Terminal Capacity
          </span>
          <div style={{
            width: '32px', height: '32px', borderRadius: '8px',
            background: 'rgba(139, 92, 246, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Server size={16} color="var(--accent-purple)" />
          </div>
        </div>
        <div className="font-mono" style={{ fontSize: '1.75rem', fontWeight: '800', color: 'var(--text-main)', marginBottom: '8px' }}>
          {activeTerminals} <span style={{ fontSize: '1rem', color: 'var(--text-dim)', fontWeight: '500' }}>/ {totalCapacity} slots</span>
        </div>
        {/* Progress Bar */}
        <div style={{ width: '100%', height: '6px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '3px', overflow: 'hidden' }}>
          <div style={{
            width: `${capacityPct}%`,
            height: '100%',
            background: capacityPct > 85 ? 'linear-gradient(90deg, #F59E0B, #F43F5E)' : 'linear-gradient(90deg, #00F2FE, #8B5CF6)',
            borderRadius: '3px',
            transition: 'width 0.5s ease'
          }}></div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.72rem', color: 'var(--text-dim)' }}>
          <span>{capacityPct}% Allocated</span>
          <span>{Math.max(0, totalCapacity - activeTerminals)} slots free</span>
        </div>
      </div>

      {/* 5. Hardware Nodes Health */}
      <div className="glass-card" style={{ padding: '20px', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', top: '-10px', right: '-10px', width: '90px', height: '90px',
          background: 'radial-gradient(circle, rgba(16, 185, 129, 0.12) 0%, transparent 70%)',
          borderRadius: '50%'
        }}></div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <span style={{ fontSize: '0.82rem', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Cluster Hardware
          </span>
          <div style={{
            width: '32px', height: '32px', borderRadius: '8px',
            background: 'rgba(16, 185, 129, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Cpu size={16} color="var(--accent-emerald)" />
          </div>
        </div>
        <div className="font-mono" style={{ fontSize: '1.75rem', fontWeight: '800', color: 'var(--text-main)', marginBottom: '4px' }}>
          {onlineNodes} <span style={{ fontSize: '1rem', color: 'var(--text-dim)', fontWeight: '500' }}>/ {totalNodes} online</span>
        </div>
        <div style={{ display: 'flex', gap: '14px', marginTop: '6px', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
          <div>Avg CPU: <span className="font-mono" style={{ color: avgCpu > 80 ? '#F43F5E' : 'var(--text-main)', fontWeight: '600' }}>{avgCpu}%</span></div>
          <div>Avg RAM: <span className="font-mono" style={{ color: avgRam > 80 ? '#F43F5E' : 'var(--text-main)', fontWeight: '600' }}>{avgRam}%</span></div>
        </div>
      </div>
    </div>
  );
}
