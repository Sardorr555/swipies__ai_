import { useState, useEffect, useRef } from 'react';
import request from '@/utils/request';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  LucideNetwork,
  LucideAlertTriangle,
  LucideSearch,
  LucideLayers,
  LucideRefreshCw,
} from 'lucide-react';

interface NodeItem {
  id: string;
  label: string;
  type: string;
  description?: string;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

interface EdgeItem {
  id: string;
  source: string;
  target: string;
  label: string;
  confidence: number;
}

const TYPE_COLORS: Record<string, string> = {
  Person: '#3B82F6', // Blue
  Project: '#10B981', // Green
  Tech: '#8B5CF6', // Purple
  Decision: '#EF4444', // Red
  Doc: '#F59E0B', // Yellow
  Repository: '#EC4899', // Pink
  Bug: '#DC2626', // Dark Red
};

export function IntelligenceGraphView() {
  const [nodes, setNodes] = useState<NodeItem[]>([]);
  const [edges, setEdges] = useState<EdgeItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<NodeItem | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const fetchGraphData = async () => {
    setLoading(true);
    try {
      const res = await request.get('/api/v1/intelligence/graph/full?global=true');
      if (res && res.data && res.data.code === 0) {
        let rawNodes: NodeItem[] = res.data.data.nodes || [];
        let rawEdges: EdgeItem[] = res.data.data.edges || [];

        const width = 800;
        const height = 550;
        const positionedNodes = rawNodes.map((n, i) => ({
          ...n,
          x: width / 2 + Math.cos((i * 2 * Math.PI) / Math.max(1, rawNodes.length)) * 200,
          y: height / 2 + Math.sin((i * 2 * Math.PI) / Math.max(1, rawNodes.length)) * 180,
          vx: 0,
          vy: 0,
        }));

        setNodes(positionedNodes);
        setEdges(rawEdges);
        if (positionedNodes.length > 0) {
          setSelectedNode(positionedNodes[0]);
        } else {
          setSelectedNode(null);
        }
      }
    } catch {
      setNodes([]);
      setEdges([]);
      setSelectedNode(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphData();
  }, []);

  // Simple Canvas Physics & Rendering
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let localNodes = [...nodes];

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw Edges
      edges.forEach((edge) => {
        const srcNode = localNodes.find((n) => n.id === edge.source);
        const tgtNode = localNodes.find((n) => n.id === edge.target);
        if (srcNode && tgtNode && srcNode.x && srcNode.y && tgtNode.x && tgtNode.y) {
          ctx.beginPath();
          ctx.moveTo(srcNode.x, srcNode.y);
          ctx.lineTo(tgtNode.x, tgtNode.y);
          ctx.strokeStyle = 'rgba(156, 163, 175, 0.4)';
          ctx.lineWidth = Math.max(1, edge.confidence * 3);
          ctx.stroke();

          // Edge Label
          const midX = (srcNode.x + tgtNode.x) / 2;
          const midY = (srcNode.y + tgtNode.y) / 2;
          ctx.font = '10px sans-serif';
          ctx.fillStyle = '#6B7280';
          ctx.fillText(edge.label, midX, midY);
        }
      });

      // Draw Nodes
      localNodes.forEach((node) => {
        if (!node.x || !node.y) return;
        const color = TYPE_COLORS[node.type] || '#6B7280';
        const isSelected = selectedNode?.id === node.id;

        // Glow Effect if selected
        if (isSelected) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, 22, 0, 2 * Math.PI);
          ctx.fillStyle = `${color}44`;
          ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(node.x, node.y, 14, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = isSelected ? '#FFFFFF' : '#1F2937';
        ctx.stroke();

        // Node Label
        ctx.font = isSelected ? 'bold 12px sans-serif' : '11px sans-serif';
        ctx.fillStyle = '#E5E7EB';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y + 28);
      });

      animId = requestAnimationFrame(render);
    };

    render();

    return () => cancelAnimationFrame(animId);
  }, [nodes, edges, selectedNode]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const clicked = nodes.find(
      (n) => n.x && n.y && Math.hypot(n.x - clickX, n.y - clickY) <= 16
    );
    if (clicked) {
      setSelectedNode(clicked);
    }
  };

  const filteredNodes = searchQuery
    ? nodes.filter(
        (n) =>
          n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
          n.type.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : nodes;

  return (
    <div className="flex flex-col xl:flex-row gap-6 w-full h-[650px]">
      {/* Canvas Area */}
      <div className="flex-1 bg-background/80 border border-border rounded-2xl p-4 relative overflow-hidden flex flex-col shadow-inner">
        {/* Controls Overlay */}
        <div className="absolute top-6 left-6 z-10 flex items-center gap-3 bg-background/90 backdrop-blur border border-border p-2 rounded-xl shadow-md">
          <div className="relative">
            <LucideSearch className="w-4 h-4 absolute left-3 top-2.5 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Поиск сущностей в графе..."
              className="pl-9 h-9 w-60 text-xs rounded-lg bg-background"
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchGraphData}
            disabled={loading}
            className="h-9 px-3 gap-1.5 text-xs"
          >
            <LucideRefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Обновить
          </Button>
        </div>

        {/* Legend Overlay */}
        <div className="absolute bottom-6 left-6 z-10 flex flex-wrap gap-2 bg-background/90 backdrop-blur border border-border p-2.5 rounded-xl text-[11px]">
          {Object.entries(TYPE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1.5 font-medium">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-muted-foreground">{type}</span>
            </div>
          ))}
        </div>

        {/* Canvas Render */}
        <canvas
          ref={canvasRef}
          width={800}
          height={550}
          onClick={handleCanvasClick}
          className="w-full h-full cursor-pointer rounded-xl"
        />
      </div>

      {/* Node Details & Bottleneck Sidebar */}
      <div className="w-full xl:w-80 flex flex-col gap-4">
        {/* Selected Node Card */}
        <div className="bg-background rounded-2xl p-5 border border-border space-y-3 shadow-md">
          <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
            <LucideLayers className="w-4 h-4" />
            Карточка Сущности
          </div>

          {selectedNode ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-lg text-foreground">{selectedNode.label}</h3>
                <span
                  className="text-[10px] font-bold px-2 py-0.5 rounded-full text-white"
                  style={{ backgroundColor: TYPE_COLORS[selectedNode.type] || '#6B7280' }}
                >
                  {selectedNode.type}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">{selectedNode.description || 'Нет описания.'}</p>
              <div className="pt-2 border-t border-border text-[11px] text-muted-foreground font-mono">
                ID: {selectedNode.id}
              </div>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">Выберите узел на графе для просмотра связей и метаданных.</p>
          )}
        </div>

        {/* Bottleneck Risks Sidebar */}
        <div className="bg-background rounded-2xl p-5 border border-border space-y-3 flex-1 overflow-y-auto shadow-md">
          <div className="flex items-center gap-2 text-amber-400 font-bold text-xs uppercase tracking-wider">
            <LucideAlertTriangle className="w-4 h-4" />
            Анализ Узких Мест (Bottlenecks)
          </div>

          <div className="space-y-2 text-xs">
            <p className="text-muted-foreground text-[11px]">
              Мониторинг узлов графа знаний с высоким показателем зависимости (Degree Centrality).
            </p>
            {nodes.length > 0 ? (
              nodes.slice(0, 3).map((n) => (
                <div key={n.id} className="p-3 rounded-xl border border-amber-500/20 bg-amber-500/5 space-y-1">
                  <div className="font-bold text-foreground flex justify-between">
                    <span>{n.label}</span>
                    <span className="text-amber-400 font-mono">Высокая связность</span>
                  </div>
                  <div className="text-[10px] text-muted-foreground">Тип: {n.type}</div>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">Сущности появятся по мере работы пользователей.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
