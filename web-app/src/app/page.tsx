import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { ArrowRight, Sparkles, Zap, Shield, Cloud } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Sparkles className="w-8 h-8 text-primary" />
            <span className="text-2xl font-bold">AI File Organizer</span>
          </div>
          <nav className="flex items-center gap-4">
            <Link href="/pricing" className="text-sm font-medium hover:text-primary">
              Pricing
            </Link>
            <Link href="/sign-in">
              <Button variant="ghost">Sign In</Button>
            </Link>
            <Link href="/sign-up">
              <Button>Get Started</Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="max-w-4xl mx-auto space-y-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-100 dark:bg-blue-900/30 rounded-full text-sm font-medium text-blue-700 dark:text-blue-300">
            <Sparkles className="w-4 h-4" />
            Powered by GPT-4, Claude, and Local AI
          </div>

          <h1 className="text-5xl md:text-6xl font-bold tracking-tight">
            Organize Your Files
            <br />
            <span className="text-primary">Automatically</span>
          </h1>

          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Let AI handle the tedious task of organizing your files. Smart categorization,
            intelligent naming, and automated organization powered by advanced AI models.
          </p>

          <div className="flex gap-4 justify-center">
            <Link href="/sign-up">
              <Button size="lg" className="gap-2">
                Start Free Trial
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
            <Link href="/demo">
              <Button size="lg" variant="outline">
                Watch Demo
              </Button>
            </Link>
          </div>

          <p className="text-sm text-muted-foreground">
            Free tier available. No credit card required.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="container mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Why Choose AI File Organizer?</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Advanced AI technology meets simple, elegant design
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          <div className="p-6 rounded-lg border bg-card">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Sparkles className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Multi-Model AI</h3>
            <p className="text-muted-foreground">
              Intelligent selection between GPT-4, Claude, and local models based on file complexity
            </p>
          </div>

          <div className="p-6 rounded-lg border bg-card">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Zap className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Lightning Fast</h3>
            <p className="text-muted-foreground">
              Process thousands of files in minutes with optimized AI model selection
            </p>
          </div>

          <div className="p-6 rounded-lg border bg-card">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Shield className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Private & Secure</h3>
            <p className="text-muted-foreground">
              Your files stay private. Local processing option available with FREE tier
            </p>
          </div>

          <div className="p-6 rounded-lg border bg-card">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Cloud className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Cloud Integration</h3>
            <p className="text-muted-foreground">
              Seamlessly integrates with OneDrive, Google Drive, and Dropbox
            </p>
          </div>
        </div>
      </section>

      {/* Pricing Preview */}
      <section className="container mx-auto px-4 py-20 bg-gray-50 dark:bg-gray-900/50 rounded-3xl">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Simple, Transparent Pricing</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Start free, upgrade when you need more power
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          <div className="p-6 rounded-lg border bg-card">
            <div className="mb-4">
              <h3 className="text-xl font-semibold mb-2">FREE</h3>
              <div className="text-3xl font-bold">$0<span className="text-sm text-muted-foreground">/month</span></div>
            </div>
            <ul className="space-y-2 mb-6">
              <li className="flex items-start gap-2">
                <span className="text-green-500">✓</span>
                <span className="text-sm">Desktop app</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500">✓</span>
                <span className="text-sm">Local AI models (Ollama)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500">✓</span>
                <span className="text-sm">Unlimited files</span>
              </li>
            </ul>
            <Link href="/sign-up">
              <Button className="w-full" variant="outline">Get Started</Button>
            </Link>
          </div>

          <div className="p-6 rounded-lg border-2 border-primary bg-card relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-primary text-primary-foreground text-xs font-medium rounded-full">
              Most Popular
            </div>
            <div className="mb-4">
              <h3 className="text-xl font-semibold mb-2">PRO</h3>
              <div className="text-3xl font-bold">$12<span className="text-sm text-muted-foreground">/month</span></div>
            </div>
            <ul className="space-y-2 mb-6">
              <li className="flex items-start gap-2">
                <span className="text-green-500">✓</span>
                <span className="text-sm">Everything in FREE</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500">✓</span>
                <span className="text-sm">GPT-4, Claude 3.5 Sonnet</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500">✓</span>
                <span className="text-sm">Web dashboard</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500">✓</span>
                <span className="text-sm">Cloud storage integration</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500">✓</span>
                <span className="text-sm">Priority support</span>
              </li>
            </ul>
            <Link href="/sign-up">
              <Button className="w-full">Start Free Trial</Button>
            </Link>
          </div>

          <div className="p-6 rounded-lg border bg-card">
            <div className="mb-4">
              <h3 className="text-xl font-semibold mb-2">ENTERPRISE</h3>
              <div className="text-3xl font-bold">Custom</div>
            </div>
            <ul className="space-y-2 mb-6">
              <li className="flex items-start gap-2">
                <span className="text-green-500">✓</span>
                <span className="text-sm">Everything in PRO</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500">✓</span>
                <span className="text-sm">Custom AI models</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500">✓</span>
                <span className="text-sm">Team collaboration</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500">✓</span>
                <span className="text-sm">API access</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500">✓</span>
                <span className="text-sm">Dedicated support</span>
              </li>
            </ul>
            <Link href="/contact">
              <Button className="w-full" variant="outline">Contact Sales</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t mt-20">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-primary" />
              <span className="font-semibold">AI File Organizer</span>
            </div>
            <p className="text-sm text-muted-foreground">
              © 2025 Alexandru Emanuel Vasile. All rights reserved.
            </p>
            <div className="flex gap-6">
              <Link href="/privacy" className="text-sm text-muted-foreground hover:text-foreground">
                Privacy
              </Link>
              <Link href="/terms" className="text-sm text-muted-foreground hover:text-foreground">
                Terms
              </Link>
              <Link href="/docs" className="text-sm text-muted-foreground hover:text-foreground">
                Docs
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
