"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Eye, EyeOff, Sprout, ArrowRight, Leaf } from "lucide-react"
import { useTranslation } from "@/app/i18n/LanguageContext"
import { API_BASE_URL } from "@/lib/config"

export default function LoginPage() {
  const { t } = useTranslation()
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setIsLoading(true)
    
    try {
      const form = e.currentTarget
      const username = (form.elements.namedItem('username') as HTMLInputElement).value
      const password = (form.elements.namedItem('password') as HTMLInputElement).value

      const response = await fetch(`${API_BASE_URL}/accounts/login/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ username, password }),
      })

      const data = await response.json()
      if (data.success) {
        router.push("/chat")
      } else {
        const errorMsg = data.errors ? Object.values(data.errors).flat().join(", ") : "Login failed"
        alert(errorMsg)
      }
    } catch (error) {
      console.error("Login failed", error)
      alert("Server error. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* Left Panel - Branding */}
      <div className="hidden flex-1 flex-col justify-between bg-sidebar p-10 lg:flex">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary">
            <Sprout className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="text-xl font-semibold text-sidebar-foreground">FarmBuddy</span>
        </div>
        
        <div className="max-w-md">
          <h1 className="text-4xl font-bold leading-tight text-sidebar-foreground">
            {t('auth.brand_title')}
          </h1>
          <p className="mt-4 text-lg text-sidebar-foreground/70">
            {t('auth.brand_description')}
          </p>
          
          <div className="mt-10 grid grid-cols-2 gap-6">
            <div className="rounded-xl border border-sidebar-border bg-sidebar-accent/50 p-5">
              <Leaf className="mb-3 h-6 w-6 text-primary" />
              <h3 className="font-medium text-sidebar-foreground">{t('auth.crop_planning')}</h3>
              <p className="mt-1 text-sm text-sidebar-foreground/60">
                {t('auth.crop_planning_desc')}
              </p>
            </div>
            <div className="rounded-xl border border-sidebar-border bg-sidebar-accent/50 p-5">
              <svg className="mb-3 h-6 w-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
              </svg>
              <h3 className="font-medium text-sidebar-foreground">{t('auth.weather_alerts')}</h3>
              <p className="mt-1 text-sm text-sidebar-foreground/60">
                {t('auth.weather_alerts_desc')}
              </p>
            </div>
          </div>
        </div>
        
        <p className="text-sm text-sidebar-foreground/50">
          {t('auth.footer_empower')}
        </p>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex flex-1 flex-col">
        {/* Mobile Header */}
        <div className="flex items-center justify-between border-b border-border p-4 lg:hidden">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <Sprout className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-lg font-semibold">FarmBuddy</span>
          </Link>
        </div>

        <div className="flex flex-1 items-center justify-center p-6 lg:p-12">
          <div className="w-full max-w-sm">
            <div className="mb-8">
              <h2 className="text-2xl font-bold tracking-tight text-foreground">{t('auth.welcome_back')}</h2>
              <p className="mt-2 text-muted-foreground">
                {t('auth.signin_subtitle')}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="username" className="text-sm font-medium">
                  {t('auth.username')}
                </Label>
                <Input
                  id="username"
                  placeholder={t('auth.username_placeholder')}
                  required
                  className="h-11 bg-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium">
                  {t('auth.password')}
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder={t('auth.password_placeholder')}
                    required
                    className="h-11 bg-input pr-11"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-11 w-11 text-muted-foreground hover:bg-transparent hover:text-foreground"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                    <span className="sr-only">
                      {showPassword ? t('settings.hide_password') : t('settings.show_password')}
                    </span>
                  </Button>
                </div>
              </div>

              <div className="flex justify-end">
                <Link
                  href="/forgot-password"
                  className="text-sm font-medium text-primary hover:underline"
                >
                  {t('auth.forgot_password')}
                </Link>
              </div>

              <Button
                type="submit"
                className="h-11 w-full gap-2"
                disabled={isLoading}
              >
                {isLoading ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                ) : (
                  <>
                    {t('auth.signin_button')}
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            <p className="mt-8 text-center text-sm text-muted-foreground">
              {t('auth.no_account')}
              <Link
                href="/signup"
                className="font-medium text-primary hover:underline"
              >
                {t('auth.signup_link')}
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
