import React from 'react';
import { Wallet, TrendingUp, Layers, ArrowUpRight, ArrowDownRight } from 'lucide-react';

export default function StatsOverview({ summary }) {
  const accounts = summary?.accounts || {};
  const nodes = summary?.nodes || {};

  const totalBalance = accounts.total_balance || 0;
  const totalEquity = accounts.total_equity || 0;
  const totalProfit = accounts.total_profit || 0;
  const isProfitPositive = totalProfit >= 0;

  const totalAccounts = accounts.total_accounts || 0;
  const activeTerminals = accounts.connected_accounts || nodes.total_active_terminals || 0;
  const openOrdersCount = accounts.total_open_positions || 0;

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      gap: '14px',
      marginBottom: '20px'
    }}>
      {/* 1. Combined Balance */}
      <div className="glass-card" style={{ padding: '16px 18px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.74rem', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Total Balance
          </span>
          <div style={{
            width: '28px', height: '28px', borderRadius: 'var(--radius-sm)',
            background: 'rgba(99, 102, 241, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Wallet size={15} color="var(--accent-indigo)" />
          </div>
        </div>
        <div className="font-mono" style={{ fontSize: '1.5rem', fontWeight: '700', color: '#ffffff' }}>
          ${totalBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
      </div>

      {/* 2. Combined Equity */}
      <div className="glass-card" style={{ padding: '16px 18px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.74rem', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Total Equity
          </span>
          <div style={{
            width: '28px', height: '28px', borderRadius: 'var(--radius-sm)',
            background: 'rgba(6, 182, 212, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <TrendingUp size={15} color="var(--accent-cyan)" />
          </div>
        </div>
        <div className="font-mono" style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--accent-cyan)' }}>
          ${totalEquity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
      </div>

      {/* 3. Floating P/L */}
      <div className="glass-card" style={{ padding: '16px 18px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.74rem', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Floating P/L
          </span>
          <div style={{
            width: '28px', height: '28px', borderRadius: 'var(--radius-sm)',
            background: isProfitPositive ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.12)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            {isProfitPositive ? <ArrowUpRight size={15} color="#10b981" /> : <ArrowDownRight size={15} color="#f43f5e" />}
          </div>
        </div>
        <div className="font-mono" style={{
          fontSize: '1.5rem',
          fontWeight: '700',
          color: isProfitPositive ? '#34d399' : '#fb7185'
        }}>
          {isProfitPositive ? '+' : ''}${totalProfit.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
      </div>

      {/* 4. Active Terminals & Orders */}
      <div className="glass-card" style={{ padding: '16px 18px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.74rem', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Terminals Online
          </span>
          <div style={{
            width: '28px', height: '28px', borderRadius: 'var(--radius-sm)',
            background: 'rgba(168, 85, 247, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Layers size={15} color="var(--accent-purple)" />
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <div className="font-mono" style={{ fontSize: '1.5rem', fontWeight: '700', color: '#ffffff' }}>
            {activeTerminals} <span style={{ fontSize: '0.88rem', color: 'var(--text-muted)', fontWeight: '500' }}>/ {totalAccounts}</span>
          </div>
          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            ({openOrdersCount} open orders)
          </span>
        </div>
      </div>
    </div>
  );
}
