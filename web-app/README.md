# AI File Organizer - Web Application

Modern web application built with Next.js 14, Clerk authentication, and Vercel deployment.

## Features

- 🔐 **Secure Authentication** - Clerk for user management and authentication
- 🎨 **Modern UI** - Tailwind CSS with Radix UI components
- 📤 **File Upload** - UploadThing integration for file management
- 🤖 **Multi-Model AI** - Integration with GPT-4, Claude, and Ollama
- ☁️ **Cloud Storage** - OneDrive, Google Drive, and Dropbox support
- 💳 **Payments** - Stripe integration for subscriptions
- 📊 **Dashboard** - Comprehensive file management interface
- 📱 **Responsive** - Mobile-friendly Progressive Web App (PWA)

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS + Radix UI
- **Authentication**: Clerk
- **File Upload**: UploadThing
- **Payments**: Stripe
- **Deployment**: Vercel
- **Database**: PostgreSQL (Supabase/Vercel Postgres)

## Prerequisites

- Node.js 18+
- npm or yarn
- Clerk account (https://clerk.com)
- UploadThing account (https://uploadthing.com)
- Stripe account (optional, for payments)

## Installation

1. **Install dependencies:**
   ```bash
   cd web-app
   npm install
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env.local
   ```

   Edit `.env.local` and fill in your credentials:
   - Clerk keys from https://dashboard.clerk.com
   - UploadThing keys from https://uploadthing.com
   - OpenAI/Anthropic API keys (optional)
   - Stripe keys (optional, for payments)

3. **Run development server:**
   ```bash
   npm run dev
   ```

   Open http://localhost:3000

## Environment Variables

### Required

- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Clerk publishable key
- `CLERK_SECRET_KEY` - Clerk secret key
- `UPLOADTHING_SECRET` - UploadThing secret
- `UPLOADTHING_APP_ID` - UploadThing app ID

### Optional (for full functionality)

- `OPENAI_API_KEY` - For GPT-4/3.5 classification
- `ANTHROPIC_API_KEY` - For Claude classification
- `DATABASE_URL` - PostgreSQL connection string
- `STRIPE_SECRET_KEY` - For payment processing
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` - Stripe public key

See `.env.example` for complete list.

## Project Structure

```
web-app/
├── src/
│   ├── app/                    # Next.js app directory
│   │   ├── (auth)/            # Auth pages (sign-in, sign-up)
│   │   ├── (dashboard)/       # Protected dashboard pages
│   │   ├── api/               # API routes
│   │   ├── layout.tsx         # Root layout
│   │   ├── page.tsx           # Home page
│   │   └── globals.css        # Global styles
│   ├── components/            # React components
│   │   ├── ui/               # UI components (buttons, cards, etc.)
│   │   ├── dashboard/        # Dashboard-specific components
│   │   └── providers/        # Context providers
│   └── lib/                   # Utility functions
│       ├── utils.ts          # Helper functions
│       ├── api.ts            # API client
│       └── store.ts          # State management (Zustand)
├── public/                    # Static assets
├── .env.example              # Environment variables template
├── next.config.js            # Next.js configuration
├── tailwind.config.ts        # Tailwind configuration
├── tsconfig.json             # TypeScript configuration
└── vercel.json               # Vercel deployment configuration
```

## Deployment to Vercel

### Automatic Deployment (Recommended)

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Complete web application"
   git push
   ```

2. **Connect to Vercel:**
   - Go to https://vercel.com
   - Click "New Project"
   - Import your GitHub repository
   - Vercel will auto-detect Next.js

3. **Configure Environment Variables:**
   - In Vercel dashboard, go to Settings → Environment Variables
   - Add all variables from `.env.local`
   - Include both development and production variables

4. **Deploy:**
   - Click "Deploy"
   - Vercel will build and deploy automatically
   - Your app will be live at `https://your-project.vercel.app`

### Manual Deployment

```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy to production
vercel --prod
```

## Custom Domain

1. Go to Vercel dashboard → Settings → Domains
2. Add your custom domain (e.g., `app.aifileorganizer.com`)
3. Update DNS records as instructed
4. Update `NEXT_PUBLIC_APP_URL` in environment variables

## Features Overview

### Landing Page
- Hero section with call-to-action
- Feature highlights
- Pricing tiers
- Footer with links

### Authentication
- Sign up / Sign in via Clerk
- Social login (Google, Microsoft)
- Email verification
- Password reset

### Dashboard
- File upload interface
- File list with categorization
- AI classification results
- Organization controls
- Settings panel

### File Upload
- Drag-and-drop interface
- Multiple file selection
- Progress indicators
- File type validation
- Size limits

### AI Classification
- Automatic categorization
- Confidence scores
- Suggested file paths
- Model selection
- Cost tracking

### Subscription Management
- Pricing page
- Stripe checkout
- Plan selection (FREE, STARTER, PRO, ENTERPRISE)
- Usage tracking
- Billing portal

## API Routes

### `/api/upload` - File Upload
POST request to upload files to UploadThing

### `/api/classify` - AI Classification
POST request to classify uploaded files

### `/api/organize` - File Organization
POST request to organize files based on classification

### `/api/webhooks/clerk` - Clerk Webhooks
Handle user creation, updates, deletions

### `/api/webhooks/stripe` - Stripe Webhooks
Handle payment events, subscription changes

## Development

### Running Tests
```bash
npm run test
```

### Type Checking
```bash
npm run type-check
```

### Linting
```bash
npm run lint
```

### Building
```bash
npm run build
```

## Performance Optimization

- **Image Optimization**: Next.js Image component
- **Code Splitting**: Automatic route-based splitting
- **Lazy Loading**: Dynamic imports for heavy components
- **Caching**: SWR for client-side data fetching
- **Bundle Analysis**: Run `npm run analyze`

## Security

- HTTPS enforced in production
- CSP headers configured
- XSS protection
- CSRF tokens
- Rate limiting on API routes
- Input validation with Zod
- SQL injection prevention (parameterized queries)

## Monitoring

### Vercel Analytics
Automatically enabled for:
- Page views
- User interactions
- Web vitals (LCP, FID, CLS)

### Error Tracking
- Built-in error boundaries
- API error logging
- User-friendly error messages

## Support

### Documentation
- Next.js: https://nextjs.org/docs
- Clerk: https://clerk.com/docs
- Tailwind: https://tailwindcss.com/docs
- Vercel: https://vercel.com/docs

### Issues
Report issues at: [Your GitHub repo]/issues

## License

Copyright © 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - See LICENSE.txt

## Pricing Tiers

- **FREE**: Desktop app only, local AI models
- **STARTER** ($5/mo): Web access, GPT-3.5, Claude Haiku
- **PRO** ($12/mo): GPT-4, Claude Sonnet, cloud storage
- **ENTERPRISE**: Custom pricing, team features, API access

## Roadmap

- [x] Landing page
- [x] Authentication with Clerk
- [x] File upload with UploadThing
- [x] AI classification
- [x] Vercel deployment
- [ ] Dashboard implementation
- [ ] Stripe payment integration
- [ ] Team collaboration features
- [ ] Mobile apps (iOS/Android)
- [ ] API access for Enterprise
- [ ] Webhook integrations
