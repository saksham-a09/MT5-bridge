import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import StatsOverview from './components/StatsOverview';
import NodeCardList from './components/NodeCardList';
import AccountsTable from './components/AccountsTable';
import AccountDetailModal from './components/AccountDetailModal';
import AddAccountModal from './components/AddAccountModal';
import BulkAddAccountsModal from './components/BulkAddAccountsModal';
import AddNodeModal from './components/AddNodeModal';
import LiveLogsDrawer from './components/LiveLogsDrawer';
import CopyTradingView from './components/CopyTradingView';

import { 
  fetchDashboardStats, fetchAccounts, fetchNodes, fetchLogs,
  startAccount, stopAccount, restartAccount, deleteAccount,
  createAccount, registerNode, deleteNode, createDashboardWebSocket,
  fetchCopyGroups, createCopyGroup, updateCopyGroup, deleteCopyGroup,
  addSlaveToGroup, removeSlaveFromGroup, fetchCopiedTrades, triggerCopierSync
} from './services/api';

export default function App() {
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard' | 'copier'
  const [summary, setSummary] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [logs, setLogs] = useState([]);
  const [copyGroups, setCopyGroups] = useState([]);
  const [copiedTrades, setCopiedTrades] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);

  // Filter states
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [nodeFilter, setNodeFilter] = useState(null);

  // Modal states
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [showAddAccountModal, setShowAddAccountModal] = useState(false);
  const [showBulkAddModal, setShowBulkAddModal] = useState(false);
  const [showAddNodeModal, setShowAddNodeModal] = useState(false);
  const [showLogsDrawer, setShowLogsDrawer] = useState(false);

  // Initial load
  const loadData = useCallback(async () => {
    try {
      const [statsRes, nodesRes, accsRes, logsRes, grpsRes, tradesRes] = await Promise.all([
        fetchDashboardStats(),
        fetchNodes(),
        fetchAccounts(),
        fetchLogs(30),
        fetchCopyGroups(),
        fetchCopiedTrades(null, 50)
      ]);
      if (statsRes?.data) setSummary(statsRes.data);
      if (nodesRes?.nodes) setNodes(nodesRes.nodes);
      if (accsRes?.accounts) setAccounts(accsRes.accounts);
      if (logsRes?.logs) setLogs(logsRes.logs);
      if (grpsRes?.groups) setCopyGroups(grpsRes.groups);
      if (tradesRes?.trades) setCopiedTrades(tradesRes.trades);
    } catch (err) {
      console.error('Data load error:', err);
    }
  }, []);

  useEffect(() => {
    loadData();

    // Setup live WebSocket
    const ws = createDashboardWebSocket(
      (data) => {
        setWsConnected(true);
        if (data.type === 'TICK') {
          if (data.summary) setSummary(data.summary);
          if (data.nodes) setNodes(data.nodes);
          if (data.accounts) setAccounts(data.accounts);
          if (data.logs) setLogs(data.logs);
          if (data.copy_groups) setCopyGroups(data.copy_groups);
          if (data.copied_trades) setCopiedTrades(data.copied_trades);
        }
      },
      () => setWsConnected(false)
    );

    return () => ws.close();
  }, [loadData]);

  // Account actions
  const handleStart = async (login) => {
    try {
      await startAccount(login);
      loadData();
    } catch (err) {
      alert('Error starting account: ' + err.message);
    }
  };

  const handleStop = async (login) => {
    try {
      await stopAccount(login);
      loadData();
    } catch (err) {
      alert('Error stopping account: ' + err.message);
    }
  };

  const handleRestart = async (login) => {
    try {
      await restartAccount(login);
      loadData();
    } catch (err) {
      alert('Error restarting account: ' + err.message);
    }
  };

  const handleDeleteAccount = async (login) => {
    try {
      await deleteAccount(login);
      loadData();
    } catch (err) {
      alert('Error deleting account: ' + err.message);
    }
  };

  const handleSaveAccount = async (formData) => {
    const res = await createAccount(formData);
    if (!res.success) throw new Error(res.message || 'Failed to save');
    loadData();
  };

  // Node actions
  const handleRegisterNode = async (nodeData) => {
    const res = await registerNode(nodeData);
    if (!res.success) throw new Error(res.message || 'Failed to register node');
    loadData();
  };

  const handleDeleteNode = async (nodeId) => {
    try {
      await deleteNode(nodeId);
      loadData();
    } catch (err) {
      alert('Error deleting node: ' + err.message);
    }
  };

  // Copier actions
  const handleCreateGroup = async (groupData) => {
    try {
      const res = await createCopyGroup(groupData);
      if (!res.success) throw new Error(res.message || 'Failed to create copy group');
      loadData();
    } catch (err) {
      alert('Error creating copy group: ' + err.message);
    }
  };

  const handleUpdateGroup = async (groupId, groupData) => {
    try {
      await updateCopyGroup(groupId, groupData);
      loadData();
    } catch (err) {
      alert('Error updating copy group: ' + err.message);
    }
  };

  const handleDeleteGroup = async (groupId) => {
    if (!confirm('Are you sure you want to delete this copy group?')) return;
    try {
      await deleteCopyGroup(groupId);
      loadData();
    } catch (err) {
      alert('Error deleting copy group: ' + err.message);
    }
  };

  const handleAddSlave = async (groupId, slaveData) => {
    try {
      const res = await addSlaveToGroup(groupId, slaveData);
      if (!res.success) throw new Error(res.message || 'Failed to add slave');
      loadData();
    } catch (err) {
      alert('Error adding slave: ' + err.message);
    }
  };

  const handleRemoveSlave = async (groupId, slaveLogin) => {
    try {
      await removeSlaveFromGroup(groupId, slaveLogin);
      loadData();
    } catch (err) {
      alert('Error removing slave: ' + err.message);
    }
  };

  const handleTriggerSync = async () => {
    try {
      await triggerCopierSync();
      loadData();
    } catch (err) {
      alert('Sync error: ' + err.message);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Navigation */}
      <Navbar
        wsConnected={wsConnected}
        nodesCount={nodes.length}
        terminalsCount={accounts.filter(a => a.status === 'active').length}
        currentView={currentView}
        onSelectView={setCurrentView}
        onAddAccount={() => setShowAddAccountModal(true)}
        onBulkImport={() => setShowBulkAddModal(true)}
        onAddNode={() => setShowAddNodeModal(true)}
        onToggleLogs={() => setShowLogsDrawer(!showLogsDrawer)}
        onRefresh={loadData}
      />

      {/* Main Content Area */}
      <main style={{ flex: 1, maxWidth: '1440px', width: '100%', margin: '0 auto', padding: '24px 32px 48px' }}>
        {currentView === 'copier' ? (
          <CopyTradingView
            summary={summary}
            groups={copyGroups}
            accounts={accounts}
            copiedTrades={copiedTrades}
            onRefresh={loadData}
            onCreateGroup={handleCreateGroup}
            onUpdateGroup={handleUpdateGroup}
            onDeleteGroup={handleDeleteGroup}
            onAddSlave={handleAddSlave}
            onRemoveSlave={handleRemoveSlave}
            onTriggerSync={handleTriggerSync}
          />
        ) : (
          <>
            {/* KPI Stats Overview */}
            <StatsOverview summary={summary} />

            {/* Distributed Worker Managers (Hardware Cluster) */}
            <NodeCardList
              nodes={nodes}
              onAddNode={() => setShowAddNodeModal(true)}
              onDeleteNode={handleDeleteNode}
              onFilterByNode={(nodeId) => setNodeFilter(nodeFilter === nodeId ? null : nodeId)}
            />

            {/* Managed Accounts Control Table */}
            <AccountsTable
              accounts={accounts}
              search={search}
              setSearch={setSearch}
              statusFilter={statusFilter}
              setStatusFilter={setStatusFilter}
              nodeFilter={nodeFilter}
              setNodeFilter={setNodeFilter}
              onStart={handleStart}
              onStop={handleStop}
              onRestart={handleRestart}
              onDelete={handleDeleteAccount}
              onSelectAccount={(acc) => setSelectedAccount(acc)}
              onBulkImport={() => setShowBulkAddModal(true)}
            />
          </>
        )}
      </main>

      {/* Modals & Drawers */}
      {selectedAccount && (
        <AccountDetailModal
          account={selectedAccount}
          onClose={() => setSelectedAccount(null)}
          onRefresh={loadData}
        />
      )}

      {showAddAccountModal && (
        <AddAccountModal
          nodes={nodes}
          onClose={() => setShowAddAccountModal(false)}
          onSave={handleSaveAccount}
          onSwitchToBulk={() => {
            setShowAddAccountModal(false);
            setShowBulkAddModal(true);
          }}
        />
      )}

      {showBulkAddModal && (
        <BulkAddAccountsModal
          nodes={nodes}
          onClose={() => setShowBulkAddModal(false)}
          onSuccess={() => {
            loadData();
          }}
        />
      )}

      {showAddNodeModal && (
        <AddNodeModal
          onClose={() => setShowAddNodeModal(false)}
          onRegistered={handleRegisterNode}
        />
      )}

      <LiveLogsDrawer
        isOpen={showLogsDrawer}
        onClose={() => setShowLogsDrawer(false)}
        logs={logs}
        onRefresh={loadData}
      />
    </div>
  );
}
