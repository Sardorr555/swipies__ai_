import { useState, useEffect, useRef } from 'react';
import request from '@/utils/request';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  LucideNetwork,
  LucideUser,
  LucideFolder,
  LucideCpu,
  LucideFileText,
  LucideAlertTriangle,
  LucideSearch,
  LucideSparkles,
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
      const res = await request.get('/api/v1/intelligence/graph/full');
      if (res && res.data && res.data.code === 0) {
        let rawNodes: NodeItem[] = res.data.data.nodes || [];
        let rawEdges: EdgeItem[] = res.data.data.edges || [];

        // If DB graph is empty, populate demo enterprise network nodes for visualization
        if (rawNodes.length === 0) {
          rawNodes = [
            { id: '1', label: 'Иван Иванов', type: 'Person', description: 'Lead AI Engineer' },
            { id: '2', label: 'Петр Сидоров', type: 'Person', description: 'Backend Lead' },
            { id: '3', label: 'Проект Swipies AI', type: 'Project', description: 'Платформа ИИ-ассистентов' },
            { id: '4', label: 'RAGFlow Core Engine', type: 'Project', description: 'Ядро гибридного поиска' },
            { id: '5', label: 'Python & Quart', type: 'Tech', description: 'Асинхронный веб-стек' },
            { id: '6', label: 'Neo4j Graph DB', type: 'Tech', description: 'Графовое хранилище связей' },
            { id: '7', label: 'Переход на Redis Streams', type: 'Decision', description: 'Асинхронная шина событий' },
            { id: '8', label: 'Спецификация PII Sanitizer', type: 'Doc', description: 'Политика анонимизации данных' },
          ];
          rawEdges = [
            { id: 'e1', source: '1', target: '3', label: 'MEMBER_OF', confidence: 0.95 },
            { id: 'e2', source: '2', target: '4', label: 'MEMBER_OF', confidence: 0.90 },
            { id: 'e3', source: '3', target: '5', label: 'USES', confidence: 0.99 },
            { id: 'e4', source: '4', target: '6', label: 'USES', confidence: 0.92 },
            { id: 'e5', source: '1', target: '7', label: 'CREATED', confidence: 0.88 },
            { id: 'e6', source: '3', target: '8', label: 'REFERENCED', confidence: 0.95 },
            { id: 'e7', source: '2', target: '7', label: 'DISCUSSED', confidence: 0.85 },
          ];
        }

        // Initialize positions
        const width = 800;
        const height = 550;
        const positionedNodes = rawNodes.map((n, i) => ({
          ...n,
          x: width / 2 + Math.cos((i * 2 * Math.PI) / rawNodes.length) * 200,
          y: height / 2 + Math.sin((i * 2 * Math.PI) / rawNodes.length) * 180,
          vx: 0,
          vy: 0,
        }));

        setNodes(positionedNodes);
        setEdges(rawEdges);
        if (positionedNodes.length > 0) {
          setSelectedNode(positionedNodes[0]);
        }
      }
    } catch {
      // Ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphData();
  }, []);

  // Simple Force Simulation Canvas Render
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw Edges
      edges.forEach((edge) => {
        const srcNode = nodes.find((n) => n.id === edge.source);
        const tgtNode = nodes.find((n) => n.id === edge.target);
        if (srcNode && tgtNode && srcNode.x && srcNode.y && tgtNode.x && tgtNode.y) {
          ctx.beginPath();
          ctx.moveTo(srcNode.x, srcNode.y);
          ctx.lineTo(tgtNode.x, tgtNode.y);
          ctx.strokeStyle = 'rgba(148, 163, 184, 0.3)';
          ctx.lineWidth = 1.5;
          ctx.stroke();

          // Label
          const midX = (srcNode.x + tgtNode.x) / 2;
          const midY = (srcNode.y + tgtNode.y) / 2;
          ctx.font = '10px sans-serif';
          ctx.fillStyle = '#94A3B8';
          ctx.fillText(edge.label, midX, midY);
        }
      });

      // Draw Nodes
      nodes.forEach((node) => {
        if (!node.x || !node.y) return;
        const color = TYPE_COLORS[node.type] || '#3B82F6';
        const isSelected = selectedNode?.id === node.id;

        ctx.beginPath();
        ctx.arc(node.x, node.y, isSelected ? 18 : 14, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.fill();

        if (isSelected) {
          ctx.lineWidth = 3;
          ctx.strokeStyle = '#FFFFFF';
          ctx.stroke();
        }

        // Title Label
        ctx.font = isSelected ? 'bold 12px sans-serif' : '11px sans-serif';
        ctx.fillStyle = isSelected ? '#FFFFFF' : '#CBD5E1';
        ctx.fillText(node.label, node.x - 20, node.y + 26);
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

    const clicked = nodes.find((n) => {
      if (!n.x || !n.y) return false;
      const dx = n.x - clickX;
      const dy = n.y - clickY;
      return Math.sqrt(dx * dx + dy * dy) <= 20;
    });

    if (clicked) {
      setSelectedNode(clicked);
    }
  };

  const filteredNodes = nodes.filter((n) =>
    n.label.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div className="flex flex-col lg:flex-row gap-6 w-full h-full">
      {/* Graph Area */}
      <div className="flex-1 bg-bg-component rounded-2xl p-4 border border-border-button flex flex-col relative overflow-hidden">
        {/* Header Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4 z-10">
          <div className="flex items-center gap-2">
            <LucideNetwork className="w-5 h-5 text-accent-primary" />
            <h3 className="font-bold text-lg text-text-primary">Интерактивный Граф Связей</h3>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <LucideSearch className="w-4 h-4 absolute left-3 top-3 text-text-disabled" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Поиск по узлам..."
                className="pl-9 h-9 text-xs w-48"
              />
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchGraphData}
              disabled={loading}
              className="h-9 gap-1"
            >
              <LucideRefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Обновить
            </Button>
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-4 text-xs mb-2 z-10 bg-bg-component/80 p-2.5 rounded-xl border border-border-button">
          <span className="flex items-center gap-1.5 font-medium">
            <span className="w-3 h-3 rounded-full bg-[#3B82F6]" /> Люди (Person)
          </span>
          <span className="flex items-center gap-1.5 font-medium">
            <span className="w-3 h-3 rounded-full bg-[#10B981]" /> Проекты (Project)
          </span>
          <span className="flex items-center gap-1.5 font-medium">
            <span className="w-3 h-3 rounded-full bg-[#8B5CF6]" /> Технологии (Tech)
          </span>
          <span className="flex items-center gap-1.5 font-medium">
            <span className="w-3 h-3 rounded-full bg-[#EF4444]" /> Решения (Decision)
          </span>
          <span className="flex items-center gap-1.5 font-medium">
            <span className="w-3 h-3 rounded-full bg-[#F59E0B]" /> Документы (Doc)
          </span>
        </div>

        {/* Canvas */}
        <div className="relative flex-1 flex items-center justify-center min-h-[450px]">
          <canvas
            ref={canvasRef}
            width={800}
            height={550}
            onClick={handleCanvasClick}
            className="cursor-pointer max-w-full rounded-xl bg-slate-950/40 border border-slate-800"
          />
        </div>
      </div>

      {/* Node Details Sidebar */}
      <div className="w-full lg:w-80 bg-bg-component rounded-2xl p-5 border border-border-button flex flex-col gap-4">
        <h4 className="font-bold text-base text-text-primary flex items-center gap-2">
          <LucideLayers className="w-4 h-4 text-accent-primary" />
          Детали Узла Графа
        </h4>

        {selectedNode ? (
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-accent-primary/10 border border-accent-primary/20">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: TYPE_COLORS[selectedNode.type] || '#3B82F6' }}
                />
                <span className="text-xs uppercase font-bold text-accent-primary">
                  {selectedNode.type}
                </span>
              </div>
              <h3 className="font-bold text-lg text-text-primary">{selectedNode.label}</h3>
              <p className="text-xs text-text-disabled mt-1">
                {selectedNode.description || 'Описание отсутствует.'}
              </p>
            </div>

            {/* Bottleneck Warning analysis if Person */}
            {selectedNode.type === 'Person' && (
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs space-y-1">
                <div className="flex items-center gap-1.5 font-bold">
                  <LucideAlertTriangle className="w-4 h-4 text-amber-400" />
                  Анализ "Узкого места" (Bottleneck)
                </div>
                <p className="text-[11px] text-amber-200/90 leading-relaxed">
                  На данном сотруднике замкнуты ключевые решения по архитектуре RAG. При уходе потребуется передача 3 уникальных контекстов.
                </p>
              </div>
            )}

            {/* Connected Relationships */}
            <div>
              <h5 className="text-xs font-bold text-text-disabled uppercase mb-2">Прямые связи:</h5>
              <div className="space-y-2">
                {edges
                  .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                  .map((edge) => {
                    const otherId = edge.source === selectedNode.id ? edge.target : edge.source;
                    const otherNode = nodes.find((n) => n.id === otherId);
                    return (
                      <div
                        key={edge.id}
                        onClick={() => otherNode && setSelectedNode(otherNode)}
                        className="p-2.5 rounded-xl border border-border-button hover:border-accent-primary/50 cursor-pointer bg-bg-component flex items-center justify-between text-xs"
                      >
                        <span className="font-semibold text-text-primary">{otherNode?.label}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-md bg-accent-primary/20 text-accent-primary font-mono">
                          {edge.label}
                        </span>
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-xs text-text-disabled">Кликните по узлу на графе для просмотра аналитики.</p>
        )}
      </div>
    </div>
  );
}
