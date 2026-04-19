"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Eye, EyeOff, Sprout, ArrowRight, ArrowLeft, Shield } from "lucide-react"
import { useTranslation } from "@/app/i18n/LanguageContext"
import { API_BASE_URL } from "@/lib/config"

type Step = "username" | "answer" | "done"

export default function ForgotPasswordPage() {
  const { t } = useTranslation()
  const router = useRouter()

  const [step, setStep] = useState<Step>("username")
  const [isLoading, setIsLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const [username, setUsername] = useState("")
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)

  const requestQuestion = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setErrorMsg(null)
    setIsLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/accounts/forgot-password/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ action: "get_question", username: username.trim() }),
      })
      const data = await res.json()
      if (data.success) {
        if (!data.has_answer) {
          setErrorMsg(t("forgot_password.error_no_question"))
          return
        }
        setQuestion(data.question)
        setStep("answer")
      } else {
        setErrorMsg(data.error || t("forgot_password.error_generic"))
      }
    } catch {
      setErrorMsg(t("forgot_password.error_generic"))
    } finally {
      setIsLoading(false)
    }
  }

  const resetPassword = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setErrorMsg(null)

    if (newPassword.length < 8) {
      setErrorMsg(t("forgot_password.error_weak_password"))
      return
    }
    if (newPassword !== confirmPassword) {
      setErrorMsg(t("forgot_password.error_password_mismatch"))
      return
    }

    setIsLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/accounts/forgot-password/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          action: "reset_password",
          username: username.trim(),
          answer: answer.trim(),
          new_password: newPassword,
        }),
      })
      const data = await res.json()
      if (data.success) {
        setStep("done")
        setTimeout(() => router.push("/login"), 1800)
      } else {
        setErrorMsg(data.error || t("forgot_password.error_generic"))
      }
    } catch {
      setErrorMsg(t("forgot_password.error_generic"))
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
            {t("forgot_password.brand_title")}
          </h1>
          <p className="mt-4 text-lg text-sidebar-foreground/70">
            {t("forgot_password.brand_description")}
          </p>

          <div className="mt-10 rounded-xl border border-sidebar-border bg-sidebar-accent/50 p-5">
            <Shield className="mb-3 h-6 w-6 text-primary" />
            <h3 className="font-medium text-sidebar-foreground">
              {t("forgot_password.security_hint_title")}
            </h3>
            <p className="mt-1 text-sm text-sidebar-foreground/60">
              {t("forgot_password.security_hint_desc")}
            </p>
          </div>
        </div>

        <p className="text-sm text-sidebar-foreground/50">
          {t("auth.footer_empower")}
        </p>
      </div>

      {/* Right Panel - Form */}
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
              <h2 className="text-2xl font-bold tracking-tight text-foreground">
                {step === "done"
                  ? t("forgot_password.success_title")
                  : t("forgot_password.title")}
              </h2>
              <p className="mt-2 text-muted-foreground">
                {step === "username" && t("forgot_password.username_subtitle")}
                {step === "answer" && t("forgot_password.answer_subtitle")}
                {step === "done" && t("forgot_password.success_message")}
              </p>
            </div>

            {errorMsg && (
              <div className="mb-5 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {errorMsg}
              </div>
            )}

            {step === "username" && (
              <form onSubmit={requestQuestion} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="username" className="text-sm font-medium">
                    {t("auth.username")}
                  </Label>
                  <Input
                    id="username"
                    placeholder={t("auth.username_placeholder")}
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="h-11 bg-input"
                  />
                </div>

                <Button type="submit" className="h-11 w-full gap-2" disabled={isLoading}>
                  {isLoading ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                  ) : (
                    <>
                      {t("forgot_password.continue_button")}
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </Button>
              </form>
            )}

            {step === "answer" && (
              <form onSubmit={resetPassword} className="space-y-5">
                <div className="space-y-2">
                  <Label className="text-sm font-medium">
                    {t("forgot_password.security_question_label")}
                  </Label>
                  <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm text-foreground">
                    {question}
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="answer" className="text-sm font-medium">
                    {t("forgot_password.security_answer_label")}
                  </Label>
                  <Input
                    id="answer"
                    placeholder={t("forgot_password.security_answer_placeholder")}
                    required
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    className="h-11 bg-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="new_password" className="text-sm font-medium">
                    {t("forgot_password.new_password_label")}
                  </Label>
                  <div className="relative">
                    <Input
                      id="new_password"
                      type={showPassword ? "text" : "password"}
                      placeholder={t("forgot_password.new_password_placeholder")}
                      required
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="h-11 bg-input pr-11"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-11 w-11 text-muted-foreground hover:bg-transparent hover:text-foreground"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirm_password" className="text-sm font-medium">
                    {t("forgot_password.confirm_password_label")}
                  </Label>
                  <Input
                    id="confirm_password"
                    type={showPassword ? "text" : "password"}
                    placeholder={t("forgot_password.confirm_password_placeholder")}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="h-11 bg-input"
                  />
                </div>

                <Button type="submit" className="h-11 w-full gap-2" disabled={isLoading}>
                  {isLoading ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                  ) : (
                    <>
                      {t("forgot_password.reset_button")}
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </Button>

                <Button
                  type="button"
                  variant="ghost"
                  className="h-11 w-full gap-2"
                  onClick={() => {
                    setStep("username")
                    setAnswer("")
                    setNewPassword("")
                    setConfirmPassword("")
                    setErrorMsg(null)
                  }}
                  disabled={isLoading}
                >
                  <ArrowLeft className="h-4 w-4" />
                  {t("forgot_password.back_button")}
                </Button>
              </form>
            )}

            {step === "done" && (
              <Button
                type="button"
                className="h-11 w-full gap-2"
                onClick={() => router.push("/login")}
              >
                {t("forgot_password.go_to_login")}
                <ArrowRight className="h-4 w-4" />
              </Button>
            )}

            <p className="mt-8 text-center text-sm text-muted-foreground">
              {t("auth.already_account")}
              <Link href="/login" className="font-medium text-primary hover:underline">
                {t("auth.signin_link")}
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
