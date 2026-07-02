'use client';

import { useEffect, useMemo } from 'react';
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { ICUAlignedState } from '@/lib/types';

interface AgentGraphProps {
  state: ICUAlignedState;
}

export function AgentGraph({ state }: AgentGraphProps) {
  const getAgentBorderColor = (agentId: 'vas' | 'lra' | 'pha' | 'nla' | 'hia') => {
    const agent = state.agent_outputs[agentId];
    if (!agent) return '#444444';
    if (agent.freshness_status === 'stale') return '#ffd000';
    if (agent.escalation_flags.length > 0) return '#ff5050';
    return '#00ff9d';
  };

  const getAgentLabel = (agentId: 'vas' | 'lra' | 'pha' | 'nla' | 'hia') => {
    const agent = state.agent_outputs[agentId];
    if (!agent) return `${agentId.toUpperCase()} (N/A)`;
    return `${agentId.toUpperCase()} (${Math.round(agent.confidence * 100)}%)`;
  };

  const initialNodes = useMemo(() => {
    const nodeStyle = (borderColor: string) => ({
      background: '#0d1b2a',
      color: '#e8edf2',
      border: `1px solid ${borderColor}`,
      borderRadius: '8px',
      padding: '8px 12px',
      fontSize: '10px',
      fontWeight: '600',
      fontFamily: 'monospace',
      textAlign: 'center' as const,
      width: 130,
      boxShadow: `0 0 10px ${borderColor}20`,
    });

    const isAlertActive = state.highest_action_tier >= 3;
    const gateBorderColor = isAlertActive ? (state.highest_action_tier === 4 ? '#ff5050' : '#ffd000') : '#00ff9d';

    return [
      // Left Layer - Input Agents
      {
        id: 'vas',
        position: { x: 20, y: 20 },
        data: { label: getAgentLabel('vas') },
        style: nodeStyle(getAgentBorderColor('vas')),
      },
      {
        id: 'lra',
        position: { x: 20, y: 100 },
        data: { label: getAgentLabel('lra') },
        style: nodeStyle(getAgentBorderColor('lra')),
      },
      {
        id: 'pha',
        position: { x: 20, y: 180 },
        data: { label: getAgentLabel('pha') },
        style: nodeStyle(getAgentBorderColor('pha')),
      },
      {
        id: 'nla',
        position: { x: 20, y: 260 },
        data: { label: getAgentLabel('nla') },
        style: nodeStyle(getAgentBorderColor('nla')),
      },
      {
        id: 'hia',
        position: { x: 20, y: 340 },
        data: { label: getAgentLabel('hia') },
        style: nodeStyle(getAgentBorderColor('hia')),
      },

      // Middle Layer - ICU Clinical Coordinator
      {
        id: 'coord',
        position: { x: 230, y: 180 },
        data: { label: `COORDINATOR\n(V${state.version})` },
        style: {
          ...nodeStyle('#00f3ff'),
          fontSize: '11px',
          background: '#050b14',
          height: 52,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        },
      },

      // Right Layer - Human Gate & Aligned State
      {
        id: 'gate',
        position: { x: 420, y: 180 },
        data: { label: `HUMAN GATE\n(T${state.highest_action_tier})` },
        style: {
          ...nodeStyle(gateBorderColor),
          fontSize: '11px',
          height: 52,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        },
      },
      {
        id: 'aligned',
        position: { x: 610, y: 180 },
        data: { label: 'ALIGNED STATE' },
        style: {
          ...nodeStyle('#00ff9d'),
          fontSize: '11px',
          height: 52,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        },
      },
    ];
  }, [state]);

  const initialEdges = useMemo(() => {
    const edgesList = [
      // Input agents to coordinator
      { id: 'e-vas', source: 'vas', target: 'coord', animated: state.agent_outputs['vas']?.freshness_status !== 'unavailable', style: { stroke: '#7a8fa8', strokeWidth: 1.5 } },
      { id: 'e-lra', source: 'lra', target: 'coord', animated: state.agent_outputs['lra']?.freshness_status !== 'unavailable', style: { stroke: '#7a8fa8', strokeWidth: 1.5 } },
      { id: 'e-pha', source: 'pha', target: 'coord', animated: state.agent_outputs['pha']?.freshness_status !== 'unavailable', style: { stroke: '#7a8fa8', strokeWidth: 1.5 } },
      { id: 'e-nla', source: 'nla', target: 'coord', animated: state.agent_outputs['nla']?.freshness_status !== 'unavailable', style: { stroke: '#7a8fa8', strokeWidth: 1.5 } },
      { id: 'e-hia', source: 'hia', target: 'coord', animated: state.agent_outputs['hia']?.freshness_status !== 'unavailable', style: { stroke: '#7a8fa8', strokeWidth: 1.5 } },

      // Coordinator to Human Gate
      { id: 'e-coord-gate', source: 'coord', target: 'gate', animated: true, style: { stroke: '#00f3ff', strokeWidth: 2 } },

      // Human Gate to Aligned State
      { id: 'e-gate-aligned', source: 'gate', target: 'aligned', animated: true, style: { stroke: '#00ff9d', strokeWidth: 2 } },
    ];

    // Check for conflicts to add a dashed red link directly between them
    state.conflicts.forEach((conflict) => {
      if (conflict.conflict_detected && conflict.conflict_agents.length >= 2) {
        const src = conflict.conflict_agents[0];
        const tgt = conflict.conflict_agents[1];
        edgesList.push({
          id: `conflict-${src}-${tgt}`,
          source: src,
          target: tgt,
          animated: false,
          style: { stroke: '#ff5050', strokeDasharray: '4,4', strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#ff5050',
          },
        } as any);
      }
    });

    return edgesList;
  }, [state]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync state updates
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [state, initialNodes, initialEdges, setNodes, setEdges]);

  return (
    <div className="w-full h-full min-h-[460px] bg-[#050b14]/40 border border-border rounded-lg relative overflow-hidden">
      <div className="absolute top-3 left-4 font-mono text-[9px] uppercase tracking-wider text-zinc-500 z-10">
        MAS Alignment Topology
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        panOnDrag={false}
        zoomOnScroll={false}
        preventScrolling={true}
        nodesConnectable={false}
        nodesDraggable={false}
      />
    </div>
  );
}
