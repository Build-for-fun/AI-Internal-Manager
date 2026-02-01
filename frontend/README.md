# AI Internal Manager - Frontend

A modern React dashboard for the AI Internal Manager system with a "Mission Control" aesthetic.

## Features

- **Dashboard**: Real-time system overview with activity charts and team health metrics
- **Chat Interface**: Multi-agent conversation UI with voice support
- **Knowledge Graph**: Interactive visualization of the company knowledge base
- **Team Analytics**: Sprint velocity, burndown charts, and bottleneck detection
- **Onboarding**: Personalized onboarding flows with progress tracking

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Framer Motion** for animations
- **Recharts** for data visualization
- **Lucide React** for icons
- **TanStack Query** for data fetching

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Development

The frontend runs on `http://localhost:3000` and proxies API requests to `http://localhost:8000`.

Make sure the backend API is running before using features that require data fetching.

## Design System

### Colors

| Variable | Color | Usage |
|----------|-------|-------|
| `--cyan` | `#00f5d4` | Primary accent, success states |
| `--violet` | `#7b61ff` | Secondary accent, links |
| `--amber` | `#ffc857` | Warnings, highlights |
| `--rose` | `#ff6b9d` | Errors, alerts |
| `--emerald` | `#10b981` | Positive trends, online status |

### Typography

- **Display**: Outfit (headings, UI text)
- **Mono**: JetBrains Mono (code, metrics, timestamps)

## Project Structure

```
frontend/
├── public/
│   └── favicon.svg
├── src/
│   ├── components/
│   │   ├── Layout.tsx        # Main layout with sidebar
│   │   ├── Dashboard.tsx     # Home dashboard
│   │   ├── ChatInterface.tsx # Chat with agents
│   │   ├── KnowledgeGraph.tsx # Knowledge visualization
│   │   ├── TeamAnalytics.tsx  # Team metrics
│   │   └── Onboarding.tsx    # Onboarding flows
│   ├── styles/
│   │   └── global.css        # Design tokens & base styles
│   ├── App.tsx               # Routes
│   └── main.tsx              # Entry point
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## API Integration

The frontend expects the backend API at `/api/v1/`. Key endpoints:

- `POST /api/v1/chat/conversations` - Create conversation
- `WS /api/v1/chat/ws/{id}` - Real-time chat
- `POST /api/v1/knowledge/search` - Search knowledge base
- `GET /api/v1/analytics/team/{id}/health` - Team metrics
- `GET /api/v1/onboarding/progress` - Onboarding status
