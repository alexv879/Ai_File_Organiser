# Next.js Web Application Setup Guide

This guide covers setting up the Next.js 14 web application with Clerk authentication and Vercel deployment.

## Project Overview

The web/mobile application provides:
- Responsive web interface (mobile-first)
- PWA support for mobile devices
- Real-time file organization
- Cloud storage integration
- Subscription management

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Authentication**: Clerk
- **Hosting**: Vercel
- **Database**: Vercel Postgres
- **Caching**: Upstash Redis
- **Styling**: Tailwind CSS + Shadcn/UI
- **State**: Zustand + TanStack Query

## Prerequisites

1. Node.js 18+ installed
2. Vercel account (https://vercel.com)
3. Clerk account (https://clerk.com)
4. GitHub account (for deployment)

## Initial Setup

### 1. Create Next.js Project

```bash
cd /home/user/Ai_File_Organiser/web-app

npx create-next-app@latest . --typescript --tailwind --app --src-dir --import-alias "@/*"

# When prompted:
# - TypeScript: Yes
# - ESLint: Yes
# - Tailwind CSS: Yes
# - `src/` directory: Yes
# - App Router: Yes
# - Customize default import alias: Yes (@/*)
```

### 2. Install Dependencies

```bash
# Authentication
npm install @clerk/nextjs

# Database & ORM
npm install @vercel/postgres drizzle-orm
npm install -D drizzle-kit

# Caching
npm install @upstash/redis @upstash/ratelimit

# State Management
npm install zustand @tanstack/react-query

# UI Components
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu
npm install @radix-ui/react-select @radix-ui/react-tabs
npm install class-variance-authority clsx tailwind-merge
npm install lucide-react

# Forms
npm install react-hook-form @hookform/resolvers zod

# File Upload
npm install react-dropzone

# Utilities
npm install date-fns axios
```

### 3. Install Shadcn/UI

```bash
npx shadcn-ui@latest init

# Select:
# - Style: Default
# - Base color: Slate
# - CSS variables: Yes
```

```bash
# Install commonly used components
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add input
npx shadcn-ui@latest add label
npx shadcn-ui@latest add select
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add table
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add progress
```

## Project Structure

```
web-app/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (auth)/
│   │   │   ├── sign-in/
│   │   │   └── sign-up/
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx       # Dashboard
│   │   │   ├── files/
│   │   │   ├── settings/
│   │   │   └── subscription/
│   │   ├── api/
│   │   │   ├── files/
│   │   │   ├── organize/
│   │   │   └── webhook/
│   │   ├── layout.tsx
│   │   └── page.tsx           # Landing page
│   │
│   ├── components/
│   │   ├── ui/                # Shadcn components
│   │   ├── dashboard/
│   │   ├── files/
│   │   └── layout/
│   │
│   ├── lib/
│   │   ├── db/
│   │   │   ├── schema.ts
│   │   │   └── queries.ts
│   │   ├── redis.ts
│   │   ├── auth.ts
│   │   └── utils.ts
│   │
│   ├── hooks/
│   │   ├── useFiles.ts
│   │   ├── useAuth.ts
│   │   └── useSubscription.ts
│   │
│   └── styles/
│       └── globals.css
│
├── public/
│   ├── icons/
│   └── manifest.json         # PWA manifest
│
├── drizzle/
│   └── migrations/
│
├── .env.local
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── drizzle.config.ts
└── package.json
```

## Configuration

### 1. Environment Variables (`.env.local`)

```bash
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
CLERK_SECRET_KEY=sk_test_xxxxx
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard

# Database (Vercel Postgres)
POSTGRES_URL=postgres://default:xxxxx@xxxxx.vercel-storage.com:5432/verceldb
POSTGRES_PRISMA_URL=postgres://default:xxxxx@xxxxx.vercel-storage.com:5432/verceldb?pgbouncer=true&connect_timeout=15
POSTGRES_URL_NON_POOLING=postgres://default:xxxxx@xxxxx.vercel-storage.com:5432/verceldb

# Redis (Upstash)
UPSTASH_REDIS_REST_URL=https://xxxxx.upstash.io
UPSTASH_REDIS_REST_TOKEN=xxxxx

# API Backend
NEXT_PUBLIC_API_URL=https://api.aifileorganizer.com
API_SECRET_KEY=your-secret-key

# Stripe (for subscriptions)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# Cloud Storage
ONEDRIVE_CLIENT_ID=xxxxx
ONEDRIVE_CLIENT_SECRET=xxxxx
GOOGLE_CLIENT_ID=xxxxx
GOOGLE_CLIENT_SECRET=xxxxx
DROPBOX_APP_KEY=xxxxx
DROPBOX_APP_SECRET=xxxxx
```

### 2. Next.js Config (`next.config.js`)

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverActions: true,
  },
  images: {
    domains: ['images.clerk.dev'],
  },
}

// PWA Configuration
const withPWA = require('next-pwa')({
  dest: 'public',
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === 'development',
})

module.exports = withPWA(nextConfig)
```

### 3. Clerk Middleware (`src/middleware.ts`)

```typescript
import { authMiddleware } from "@clerk/nextjs";

export default authMiddleware({
  publicRoutes: ["/", "/api/webhook"],
  ignoredRoutes: ["/api/public"],
});

export const config = {
  matcher: ['/((?!.+\\.[\\w]+$|_next).*)', '/', '/(api|trpc)(.*)'],
};
```

### 4. Database Schema (`src/lib/db/schema.ts`)

```typescript
import { pgTable, serial, text, timestamp, integer, boolean } from 'drizzle-orm/pg-core';

export const users = pgTable('users', {
  id: serial('id').primaryKey(),
  clerkId: text('clerk_id').notNull().unique(),
  email: text('email').notNull(),
  subscriptionTier: text('subscription_tier').default('free'),
  subscriptionStatus: text('subscription_status'),
  createdAt: timestamp('created_at').defaultNow(),
});

export const files = pgTable('files', {
  id: serial('id').primaryKey(),
  userId: integer('user_id').notNull(),
  fileName: text('file_name').notNull(),
  filePath: text('file_path').notNull(),
  category: text('category'),
  size: integer('size'),
  cloudProvider: text('cloud_provider'),
  cloudFileId: text('cloud_file_id'),
  status: text('status').default('pending'),
  createdAt: timestamp('created_at').defaultNow(),
  organizedAt: timestamp('organized_at'),
});

export const subscriptions = pgTable('subscriptions', {
  id: serial('id').primaryKey(),
  userId: integer('user_id').notNull(),
  stripeCustomerId: text('stripe_customer_id'),
  stripeSubscriptionId: text('stripe_subscription_id'),
  tier: text('tier').notNull(), // 'free', 'starter', 'pro', 'business'
  status: text('status').notNull(),
  currentPeriodEnd: timestamp('current_period_end'),
  createdAt: timestamp('created_at').defaultNow(),
});
```

### 5. Drizzle Config (`drizzle.config.ts`)

```typescript
import type { Config } from 'drizzle-kit';

export default {
  schema: './src/lib/db/schema.ts',
  out: './drizzle',
  driver: 'pg',
  dbCredentials: {
    connectionString: process.env.POSTGRES_URL!,
  },
} satisfies Config;
```

## Key Implementations

### 1. Dashboard Layout (`src/app/(dashboard)/layout.tsx`)

```typescript
import { auth } from '@clerk/nextjs';
import { redirect } from 'next/navigation';
import { Navbar } from '@/components/layout/Navbar';
import { Sidebar } from '@/components/layout/Sidebar';

export default async function DashboardLayout({
  children,
}: {
  children: React.Node;
}) {
  const { userId } = auth();

  if (!userId) {
    redirect('/sign-in');
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto bg-gray-50 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
```

### 2. File Upload Component (`src/components/files/FileUpload.tsx`)

```typescript
'use client';

import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload } from 'lucide-react';

export function FileUpload() {
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    for (const file of acceptedFiles) {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/files/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        console.log('File uploaded:', file.name);
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
  });

  return (
    <div
      {...getRootProps()}
      className={`
        border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
        transition-colors
        ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
      `}
    >
      <input {...getInputProps()} />
      <Upload className="mx-auto h-12 w-12 text-gray-400" />
      <p className="mt-2 text-sm text-gray-600">
        {isDragActive
          ? 'Drop files here...'
          : 'Drag and drop files, or click to select'}
      </p>
    </div>
  );
}
```

### 3. API Route - File Organization (`src/app/api/organize/route.ts`)

```typescript
import { auth } from '@clerk/nextjs';
import { NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { files } from '@/lib/db/schema';

export async function POST(req: Request) {
  const { userId } = auth();

  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { fileId } = await req.json();

  // Call Python backend for classification
  const response = await fetch(`${process.env.API_URL}/api/classify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.API_SECRET_KEY}`,
    },
    body: JSON.stringify({ fileId }),
  });

  const classification = await response.json();

  // Update database
  await db.update(files)
    .set({
      category: classification.category,
      status: 'organized',
      organizedAt: new Date(),
    })
    .where({ id: fileId });

  return NextResponse.json(classification);
}
```

## PWA Setup

### 1. Install PWA Package

```bash
npm install next-pwa
```

### 2. Create Manifest (`public/manifest.json`)

```json
{
  "name": "AI File Organizer",
  "short_name": "AIFO",
  "description": "AI-powered file organization",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#3b82f6",
  "icons": [
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

### 3. Add to Layout (`src/app/layout.tsx`)

```typescript
export const metadata = {
  manifest: '/manifest.json',
  themeColor: '#3b82f6',
};
```

## Deployment to Vercel

### 1. Connect GitHub Repository

```bash
# Initialize git (if not already)
git init
git add .
git commit -m "Initial commit"

# Push to GitHub
git remote add origin https://github.com/yourusername/ai-file-organizer-web.git
git push -u origin main
```

### 2. Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel

# Deploy to production
vercel --prod
```

### 3. Set Environment Variables in Vercel

1. Go to Vercel Dashboard
2. Select your project
3. Settings → Environment Variables
4. Add all variables from `.env.local`

### 4. Enable Vercel Postgres

```bash
# In Vercel Dashboard
# Storage → Create Database → Postgres
# Copy connection strings to Environment Variables
```

### 5. Run Database Migrations

```bash
# Generate migrations
npx drizzle-kit generate:pg

# Push to database
npx drizzle-kit push:pg
```

## Testing

```bash
# Install testing dependencies
npm install -D @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom

# Run tests
npm test

# E2E tests
npm install -D @playwright/test
npx playwright test
```

## Production Checklist

- [ ] Enable HTTPS (automatic on Vercel)
- [ ] Set up custom domain
- [ ] Configure CDN caching
- [ ] Enable rate limiting
- [ ] Set up monitoring (Sentry, LogRocket)
- [ ] Configure analytics (Plausible, PostHog)
- [ ] Test PWA installation
- [ ] Optimize images (next/image)
- [ ] Enable compression
- [ ] Set up status page
- [ ] Configure backup strategy

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Clerk Documentation](https://clerk.com/docs)
- [Vercel Documentation](https://vercel.com/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Shadcn/UI](https://ui.shadcn.com/)
