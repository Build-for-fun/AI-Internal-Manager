import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  Filter,
  ZoomIn,
  ZoomOut,
  Maximize2,
  ChevronRight,
  FileText,
  Folder,
  Code,
  BookOpen,
  X,
  ExternalLink,
  Clock,
} from 'lucide-react'
import { useRbac } from '../contexts/RbacContext'

interface Node {
  id: string
  label: string
  type: 'department' | 'topic' | 'context' | 'person' | 'document'
  x: number
  y: number
  connections: string[]
}

interface KnowledgeItem {
  id: string
  title: string
  type: string
  department: string
  lastUpdated: string
  summary: string
}

// Simulated graph data
const graphNodes: Node[] = [
  { id: '1', label: 'Engineering', type: 'department', x: 400, y: 200, connections: ['2', '3', '4'] },
  { id: '2', label: 'Platform', type: 'topic', x: 250, y: 100, connections: ['5', '6'] },
  { id: '3', label: 'Backend', type: 'topic', x: 550, y: 100, connections: ['7', '8'] },
  { id: '4', label: 'Frontend', type: 'topic', x: 400, y: 350, connections: ['9'] },
  { id: '5', label: 'Auth Service', type: 'context', x: 150, y: 50, connections: [] },
  { id: '6', label: 'API Gateway', type: 'context', x: 300, y: 30, connections: [] },
  { id: '7', label: 'Database', type: 'context', x: 500, y: 30, connections: [] },
  { id: '8', label: 'Microservices', type: 'context', x: 650, y: 50, connections: [] },
  { id: '9', label: 'React Patterns', type: 'context', x: 400, y: 450, connections: [] },
]

const sampleKnowledge: KnowledgeItem[] = [
  {
    id: '1',
    title: 'Authentication Service Architecture',
    type: 'document',
    department: 'Platform',
    lastUpdated: '2 days ago',
    summary: 'Comprehensive guide to our JWT-based authentication system including OAuth2 integration.',
  },
  {
    id: '2',
    title: 'API Rate Limiting Guidelines',
    type: 'policy',
    department: 'Platform',
    lastUpdated: '1 week ago',
    summary: 'Standards for implementing rate limiting across all public and internal APIs.',
  },
  {
    id: '3',
    title: 'Database Migration Procedures',
    type: 'runbook',
    department: 'Backend',
    lastUpdated: '3 days ago',
    summary: 'Step-by-step procedures for safely migrating database schemas in production.',
  },
  {
    id: '4',
    title: 'React Component Library',
    type: 'documentation',
    department: 'Frontend',
    lastUpdated: '1 day ago',
    summary: 'Documentation for our internal component library with usage examples.',
  },
]

const typeColors = {
  department: 'var(--violet)',
  topic: 'var(--cyan)',
  context: 'var(--amber)',
  person: 'var(--emerald)',
  document: 'var(--rose)',
}

const typeIcons = {
  document: FileText,
  policy: BookOpen,
  runbook: Code,
  documentation: Folder,
}

export default function KnowledgeGraph() {
  const { knowledgeScope } = useRbac()
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [zoom, setZoom] = useState(1)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const canvasRef = useRef<HTMLDivElement>(null)

  const scopeLabel = (() => {
    const filters = (knowledgeScope?.filters || {}) as Record<string, string>
    if (filters.department_id) return `Department • ${filters.department_id}`
    if (filters.team_id) return `Team • ${filters.team_id}`
    if (filters.owner_id) return 'Personal'
    return 'Company'
  })()

  return (
    <div style={styles.container}>
      {/* Left panel - Graph visualization */}
      <div style={styles.graphPanel}>
        {/* Toolbar */}
        <div style={styles.toolbar}>
          <div style={styles.searchBox}>
            <Search size={16} style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search knowledge graph..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={styles.searchInput}
            />
          </div>

          <div style={styles.toolbarActions}>
            <motion.button
              style={styles.toolbarBtn}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Filter size={16} />
            </motion.button>
            <span style={styles.scopePill}>Scope: {scopeLabel}</span>
            <div style={styles.zoomControls}>
              <motion.button
                style={styles.toolbarBtn}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setZoom(Math.max(0.5, zoom - 0.1))}
              >
                <ZoomOut size={16} />
              </motion.button>
              <span style={styles.zoomLevel}>{Math.round(zoom * 100)}%</span>
              <motion.button
                style={styles.toolbarBtn}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setZoom(Math.min(2, zoom + 0.1))}
              >
                <ZoomIn size={16} />
              </motion.button>
            </div>
            <motion.button
              style={styles.toolbarBtn}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Maximize2 size={16} />
            </motion.button>
          </div>
        </div>

        {/* Graph canvas */}
        <div ref={canvasRef} style={styles.canvas}>
          <svg
            width="100%"
            height="100%"
            style={{ position: 'absolute', inset: 0, transform: `scale(${zoom})` }}
          >
            {/* Connections */}
            {graphNodes.map((node) =>
              node.connections.map((targetId) => {
                const target = graphNodes.find((n) => n.id === targetId)
                if (!target) return null
                const isHighlighted = hoveredNode === node.id || hoveredNode === targetId
                return (
                  <motion.line
                    key={`${node.id}-${targetId}`}
                    x1={node.x}
                    y1={node.y}
                    x2={target.x}
                    y2={target.y}
                    stroke={isHighlighted ? 'var(--cyan)' : 'var(--border)'}
                    strokeWidth={isHighlighted ? 2 : 1}
                    strokeOpacity={isHighlighted ? 1 : 0.5}
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 1, delay: 0.2 }}
                  />
                )
              })
            )}
          </svg>

          {/* Nodes */}
          {graphNodes.map((node, index) => (
            <motion.div
              key={node.id}
              style={{
                ...styles.graphNode,
                left: node.x * zoom,
                top: node.y * zoom,
                borderColor: typeColors[node.type],
                background:
                  hoveredNode === node.id || selectedNode?.id === node.id
                    ? `${typeColors[node.type]}20`
                    : 'var(--surface)',
              }}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: index * 0.05, type: 'spring', stiffness: 500 }}
              whileHover={{ scale: 1.1 }}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              onClick={() => setSelectedNode(node)}
            >
              <span
                style={{
                  ...styles.nodeDot,
                  background: typeColors[node.type],
                }}
              />
              <span style={styles.nodeLabel}>{node.label}</span>
            </motion.div>
          ))}
        </div>

        {/* Legend */}
        <div style={styles.legend}>
          {Object.entries(typeColors).map(([type, color]) => (
            <div key={type} style={styles.legendItem}>
              <span style={{ ...styles.legendDot, background: color }} />
              <span style={styles.legendLabel}>{type}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel - Knowledge list */}
      <div style={styles.listPanel}>
        <div style={styles.listHeader}>
          <h3 style={styles.listTitle}>Knowledge Base</h3>
          <span style={styles.listCount}>{sampleKnowledge.length} items</span>
        </div>

        {/* Breadcrumb */}
        <div style={styles.breadcrumb}>
          <span style={styles.breadcrumbItem}>All</span>
          <ChevronRight size={14} style={{ color: 'var(--text-dim)' }} />
          <span style={styles.breadcrumbItem}>Engineering</span>
          {selectedNode && (
            <>
              <ChevronRight size={14} style={{ color: 'var(--text-dim)' }} />
              <span style={styles.breadcrumbCurrent}>{selectedNode.label}</span>
            </>
          )}
        </div>

        {/* Knowledge list */}
        <div style={styles.knowledgeList}>
          <AnimatePresence>
            {sampleKnowledge.map((item, index) => {
              const Icon = typeIcons[item.type as keyof typeof typeIcons] || FileText
              return (
                <motion.div
                  key={item.id}
                  style={styles.knowledgeCard}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  whileHover={{
                    borderColor: 'var(--cyan)',
                    background: 'var(--elevated)',
                  }}
                >
                  <div style={styles.cardIcon}>
                    <Icon size={20} />
                  </div>
                  <div style={styles.cardContent}>
                    <div style={styles.cardHeader}>
                      <h4 style={styles.cardTitle}>{item.title}</h4>
                      <motion.button
                        style={styles.cardAction}
                        whileHover={{ color: 'var(--cyan)' }}
                      >
                        <ExternalLink size={14} />
                      </motion.button>
                    </div>
                    <p style={styles.cardSummary}>{item.summary}</p>
                    <div style={styles.cardMeta}>
                      <span className="badge">{item.type}</span>
                      <span className="badge violet">{item.department}</span>
                      <span style={styles.cardTime}>
                        <Clock size={12} />
                        {item.lastUpdated}
                      </span>
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </AnimatePresence>
        </div>

        {/* Selected node details */}
        <AnimatePresence>
          {selectedNode && (
            <motion.div
              style={styles.nodeDetails}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
            >
              <div style={styles.detailsHeader}>
                <div>
                  <span
                    className="badge"
                    style={{
                      background: `${typeColors[selectedNode.type]}20`,
                      color: typeColors[selectedNode.type],
                      borderColor: `${typeColors[selectedNode.type]}40`,
                    }}
                  >
                    {selectedNode.type}
                  </span>
                  <h4 style={styles.detailsTitle}>{selectedNode.label}</h4>
                </div>
                <motion.button
                  style={styles.closeBtn}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={() => setSelectedNode(null)}
                >
                  <X size={16} />
                </motion.button>
              </div>
              <div style={styles.detailsStats}>
                <div style={styles.detailsStat}>
                  <span style={styles.statValue}>{selectedNode.connections.length}</span>
                  <span style={styles.statLabel}>Connections</span>
                </div>
                <div style={styles.detailsStat}>
                  <span style={styles.statValue}>24</span>
                  <span style={styles.statLabel}>Documents</span>
                </div>
                <div style={styles.detailsStat}>
                  <span style={styles.statValue}>12</span>
                  <span style={styles.statLabel}>Contributors</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'grid',
    gridTemplateColumns: '1fr 400px',
    gap: 'var(--space-lg)',
    height: 'calc(100vh - 64px - 48px)',
  },
  graphPanel: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 'var(--space-md) var(--space-lg)',
    borderBottom: '1px solid var(--border)',
    background: 'var(--elevated)',
  },
  searchBox: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-sm) var(--space-md)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    width: '280px',
  },
  searchInput: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: 'var(--text-primary)',
    fontSize: '0.875rem',
  },
  toolbarActions: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
  },
  scopePill: {
    padding: '4px 10px',
    borderRadius: '999px',
    fontSize: '0.6875rem',
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
    background: 'rgba(0, 245, 212, 0.12)',
    color: 'var(--cyan)',
    border: '1px solid rgba(0, 245, 212, 0.25)',
  },
  toolbarBtn: {
    width: '32px',
    height: '32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
  },
  zoomControls: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-xs)',
    padding: '0 var(--space-sm)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
  },
  zoomLevel: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
    width: '40px',
    textAlign: 'center',
  },
  canvas: {
    flex: 1,
    position: 'relative',
    overflow: 'hidden',
    background:
      'radial-gradient(circle at 50% 50%, var(--elevated) 0%, var(--surface) 100%)',
  },
  graphNode: {
    position: 'absolute',
    transform: 'translate(-50%, -50%)',
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-sm) var(--space-md)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-full)',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    zIndex: 10,
  },
  nodeDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  nodeLabel: {
    fontSize: '0.8125rem',
    fontWeight: 500,
    color: 'var(--text-primary)',
  },
  legend: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-lg)',
    padding: 'var(--space-md) var(--space-lg)',
    borderTop: '1px solid var(--border)',
    background: 'var(--elevated)',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-xs)',
  },
  legendDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  legendLabel: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
    textTransform: 'capitalize',
  },
  listPanel: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  listHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 'var(--space-md) var(--space-lg)',
    borderBottom: '1px solid var(--border)',
  },
  listTitle: {
    fontSize: '1rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  listCount: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
  },
  breadcrumb: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-xs)',
    padding: 'var(--space-sm) var(--space-lg)',
    borderBottom: '1px solid var(--border)',
    background: 'var(--abyss)',
  },
  breadcrumbItem: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
    cursor: 'pointer',
  },
  breadcrumbCurrent: {
    fontSize: '0.75rem',
    color: 'var(--cyan)',
    fontWeight: 500,
  },
  knowledgeList: {
    flex: 1,
    overflowY: 'auto',
    padding: 'var(--space-md)',
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-sm)',
  },
  knowledgeCard: {
    display: 'flex',
    gap: 'var(--space-md)',
    padding: 'var(--space-md)',
    background: 'var(--abyss)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  cardIcon: {
    width: '40px',
    height: '40px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--elevated)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-secondary)',
    flexShrink: 0,
  },
  cardContent: {
    flex: 1,
    minWidth: 0,
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 'var(--space-sm)',
    marginBottom: 'var(--space-xs)',
  },
  cardTitle: {
    fontSize: '0.875rem',
    fontWeight: 500,
    color: 'var(--text-primary)',
    lineHeight: 1.3,
  },
  cardAction: {
    background: 'none',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    padding: '2px',
  },
  cardSummary: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
    lineHeight: 1.4,
    marginBottom: 'var(--space-sm)',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  cardMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-xs)',
    flexWrap: 'wrap',
  },
  cardTime: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '0.6875rem',
    color: 'var(--text-dim)',
    marginLeft: 'auto',
  },
  nodeDetails: {
    padding: 'var(--space-lg)',
    borderTop: '1px solid var(--border)',
    background: 'var(--elevated)',
  },
  detailsHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: 'var(--space-md)',
  },
  detailsTitle: {
    fontSize: '1rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginTop: 'var(--space-xs)',
  },
  closeBtn: {
    width: '28px',
    height: '28px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-muted)',
    cursor: 'pointer',
  },
  detailsStats: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 'var(--space-md)',
  },
  detailsStat: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: 'var(--space-sm)',
    background: 'var(--surface)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border)',
  },
  statValue: {
    fontSize: '1.25rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
  },
  statLabel: {
    fontSize: '0.6875rem',
    color: 'var(--text-muted)',
  },
}
