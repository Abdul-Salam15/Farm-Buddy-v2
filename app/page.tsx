"use client"

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
import { useTranslation } from "@/app/i18n/LanguageContext"

export default function HomePage() {
  const { t } = useTranslation()

  const features = [
    {
      icon: MessageSquare,
      title: t("features.ai_advice_title"),
      description: t("features.ai_advice_desc"),
    },
    {
      icon: Cloud,
      title: t("features.weather_title"),
      description: t("features.weather_desc"),
    },
    {
      icon: Leaf,
      title: t("features.crop_mgmt_title"),
      description: t("features.crop_mgmt_desc"),
    },
    {
      icon: Shield,
      title: t("features.pest_control_title"),
      description: t("features.pest_control_desc"),
    },
  ]

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/80 backdrop-blur-sm">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Sprout className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="text-lg font-semibold">{t("common.farmbuddy")}</span>
          </Link>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/login">{t("common.sign_in")}</Link>
            </Button>
            <Button size="sm" asChild>
              <Link href="/signup">{t("common.get_started")}</Link>
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
              <span>{t("home.hero_badge")}</span>
            </div>
            <h1 className="text-balance text-4xl font-bold tracking-tight md:text-5xl lg:text-6xl">
              {t("home.hero_title_1")}
              <span className="text-primary">{t("home.hero_title_2")}</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-pretty text-lg text-muted-foreground">
              {t("home.hero_description")}
            </p>
            <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Button size="lg" asChild className="gap-2">
                <Link href="/signup">
                  {t("home.start_free")}
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/login">{t("home.sign_in_account")}</Link>
              </Button>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="border-t border-border bg-muted/30 py-20">
          <div className="container mx-auto px-4">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-bold">{t("home.features_title")}</h2>
              <p className="mt-4 text-muted-foreground">
                {t("home.features_description")}
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
              <h2 className="text-2xl font-bold md:text-3xl">{t("home.cta_title")}</h2>
              <p className="mt-4 text-muted-foreground">
                {t("home.cta_description")}
              </p>
              <Button size="lg" asChild className="mt-8 gap-2">
                <Link href="/signup">
                  {t("home.get_started_today")}
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
            <span className="text-sm font-medium">{t("common.farmbuddy")}</span>
          </div>
          <p className="text-sm text-muted-foreground">
            {t("home.footer_description")}
          </p>
        </div>
      </footer>
    </div>
  )
}
