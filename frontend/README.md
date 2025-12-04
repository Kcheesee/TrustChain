# TrustChain Dashboard

Real-time AI decision monitoring dashboard for TrustChain.

Built with care by Kareem & Claude

## Features

- **Real-time Decision Feed**: Live stream of AI decisions via WebSocket
- **Metrics Dashboard**: Approval rates, confidence scores, throughput
- **Fairness Monitoring**: Bias detection rates and counterfactual fairness scores
- **Alerts Panel**: System notifications and bias alerts
- **Connection Status**: Visual WebSocket connection indicator with auto-reconnect

## Tech Stack

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Recharts (for future charts)

## Quick Start

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

## Configuration

The dashboard connects to the TrustChain API at `localhost:8000` by default.

For development, the Vite dev server proxies API and WebSocket requests:
- `/api/*` → `http://localhost:8000`
- `/ws/*` → `ws://localhost:8000`

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.tsx      # Main dashboard component
│   │   ├── MetricsCard.tsx    # Individual metric display
│   │   ├── DecisionFeed.tsx   # Live decision stream
│   │   ├── AlertsPanel.tsx    # Alerts display
│   │   └── ConnectionStatus.tsx # WebSocket status
│   ├── hooks/
│   │   └── useWebSocket.ts    # WebSocket connection hook
│   ├── types/
│   │   └── index.ts           # TypeScript type definitions
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## Environment Variables

Create a `.env` file for custom configuration:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Docker

Build the frontend for Docker:

```bash
npm run build
```

The `dist/` folder can be served by any static file server (nginx, etc.)
