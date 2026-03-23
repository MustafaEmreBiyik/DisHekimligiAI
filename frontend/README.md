# DentAI Frontend

The DentAI frontend is a Next.js application for the dental education simulator. It provides the student-facing experience for authentication, case browsing, chat-based patient interaction, quiz flows, and performance views.

## Tech Stack

- Next.js 16 with the App Router
- React 19
- TypeScript
- Axios for API requests
- Recharts for data visualizations
- CSS Modules and global styles

## Prerequisites

Before starting, make sure you have:

- Node.js 18 or newer
- npm
- The DentAI backend running locally

## Getting Started

Install dependencies:

```bash
npm install
```

Create a `.env.local` file in `frontend/`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the development server:

```bash
npm run dev
```

Open `http://localhost:3000` in your browser.

## Available Scripts

- `npm run dev` starts the development server
- `npm run build` creates a production build
- `npm run start` runs the production build locally
- `npm run lint` runs ESLint

## Backend Dependency

This app talks to the DentAI FastAPI backend through the Axios client in `lib/api.ts`. If the backend is not running or `NEXT_PUBLIC_API_URL` is incorrect, login, case loading, chat, analytics exports, and feedback submission will fail.

Default local backend URL:

```text
http://localhost:8000
```

## Main Routes

- `/` landing page
- `/login` student login
- `/register` student registration
- `/dashboard` case overview
- `/cases` case listing
- `/chat/[case_id]` case conversation
- `/quiz` quiz flow
- `/profile` student profile
- `/statistics` statistics page
- `/stats` additional stats view
- `/medgemma` MedGemma-related page

## Project Structure

```text
frontend/
|-- app/                 Next.js App Router pages
|-- components/          Shared UI components such as layout and chat pieces
|-- context/             Global React context providers
|-- lib/                 API client and frontend utilities
|-- public/              Static assets
|-- package.json         Scripts and dependencies
|-- tsconfig.json        TypeScript configuration
`-- README.md            Frontend documentation
```

## Authentication Flow

- Authentication state is managed in `context/AuthContext.tsx`
- JWT tokens are stored in `localStorage`
- The Axios client automatically attaches the bearer token to requests
- `401` responses clear stored credentials and redirect the user to `/login`

## Notes for Development

- The sidebar is hidden on `/`, `/login`, and `/register`
- Most pages depend on backend API responses, so frontend work is easier to verify with the API running
- Analytics downloads open backend export endpoints in a new browser tab

## Related Files

- Root project docs: `../README.md`
- API client: `lib/api.ts`
- Auth context: `context/AuthContext.tsx`
- Root layout wrapper: `components/AppLayout.tsx`
