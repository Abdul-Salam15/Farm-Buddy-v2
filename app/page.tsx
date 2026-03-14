import Link from "next/link"
import { Button } from "@/components/ui/button"
import {
  Sprout,
  ArrowRight,
  MessageSquare,
  Cloud,
  Leaf,
  Shield,
} from "lucide-react"

const features = [
  {
    icon: MessageSquare,
    title: "AI-Powered Advice",
    description: "Get instant answers to your farming questions from our intelligent agricultural advisor.",
  },
  {
    icon: Cloud,
    title: "Weather Forecasts",
    description: "Stay ahead with accurate weather predictions tailored to your farm location.",
  },
  {
    icon: Leaf,
    title: "Crop Management",
    description: "Optimize your planting schedules and get personalized crop recommendations.",
  },
  {
    icon: Shield,
    title: "Pest Control",
    description: "Identify and manage pests effectively with AI-driven solutions.",
  },
]

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/80 backdrop-blur-sm">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Sprout className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="text-lg font-semibold">FarmBuddy</span>
          </Link>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/login">Sign in</Link>
            </Button>
            <Button size="sm" asChild>
              <Link href="/signup">Get Started</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1">
        <section className="container mx-auto px-4 py-20 text-center md:py-32">
          <div className="mx-auto max-w-3xl">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-muted/50 px-4 py-1.5 text-sm">
              <Sprout className="h-4 w-4 text-primary" />
              <span>AI-Powered Agricultural Advisor</span>
            </div>
            <h1 className="text-balance text-4xl font-bold tracking-tight md:text-5xl lg:text-6xl">
              Grow smarter with
              <span className="text-primary"> AI assistance</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-pretty text-lg text-muted-foreground">
              FarmBuddy is your intelligent farming companion. Get personalized advice, weather forecasts, and crop management tips designed for Nigerian smallholder farmers.
            </p>
            <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Button size="lg" asChild className="gap-2">
                <Link href="/signup">
                  Start for free
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/login">Sign in to your account</Link>
              </Button>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="border-t border-border bg-muted/30 py-20">
          <div className="container mx-auto px-4">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-bold">Everything you need to succeed</h2>
              <p className="mt-4 text-muted-foreground">
                Powerful tools and insights to help you make better farming decisions.
              </p>
            </div>
            <div className="mx-auto mt-16 grid max-w-5xl gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {features.map((feature) => (
                <div
                  key={feature.title}
                  className="rounded-xl border border-border bg-card p-6 transition-colors hover:border-primary/50"
                >
                  <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10">
                    <feature.icon className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="mt-4 font-semibold">{feature.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20">
          <div className="container mx-auto px-4 text-center">
            <div className="mx-auto max-w-2xl rounded-2xl border border-border bg-card p-8 md:p-12">
              <h2 className="text-2xl font-bold md:text-3xl">Ready to transform your farming?</h2>
              <p className="mt-4 text-muted-foreground">
                Join thousands of farmers already using FarmBuddy to improve their yields.
              </p>
              <Button size="lg" asChild className="mt-8 gap-2">
                <Link href="/signup">
                  Get started today
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border py-8">
        <div className="container mx-auto flex flex-col items-center justify-between gap-4 px-4 text-center sm:flex-row sm:text-left">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-primary">
              <Sprout className="h-3 w-3 text-primary-foreground" />
            </div>
            <span className="text-sm font-medium">FarmBuddy</span>
          </div>
          <p className="text-sm text-muted-foreground">
            Empowering Nigerian smallholder farmers with AI technology.
          </p>
        </div>
      </footer>
    </div>
  )
}
