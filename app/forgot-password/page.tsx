"use client"

import { useState, useEffect, useRef } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Eye, EyeOff, Sprout, ArrowRight, ArrowLeft, Shield, Mail, HelpCircle } from "lucide-react"
import { useTranslation } from "@/app/i18n/LanguageContext"
import { API_BASE_URL } from "@/lib/config"

type Step = "username" | "choose_method" | "otp" | "set_password" | "answer" | "done"

export default function ForgotPasswordPage() {
  const { t } = useTranslation()
  const router = useRouter()

  const [step, setStep] = useState<Step>("username")
  const [isLoading, setIsLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Shared state
  const [username, setUsername] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)

  // Security question state
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState("")
  const [hasEmail, setHasEmail] = useState(false)
  const [hasAnswer, setHasAnswer] = useState(false)

  // OTP state
  const [emailHint, setEmailHint] = useState("")
  const [otpDigits, setOtpDigits] = useState(["", "", "", "", "", ""])
  const [resendCooldown, setResendCooldown] = useState(0)
  const otpRefs = useRef<(HTMLInputElement | null)[]>([])

  // Countdown timer for OTP resend
  useEffect(() => {
    if (resendCooldown <= 0) return
    const id = setInterval(() => setResendCooldown(s => s - 1), 1000)
    return () => clearInterval(id)
  }, [resendCooldown])

  const resetBack = () => {
    setErrorMsg(null)
    setAnswer("")
    setNewPassword("")
    setConfirmPassword("")
    setOtpDigits(["", "", "", "", "", ""])
  }

  // ── Step 1: look up username ──────────────────────────────────────────────
  const requestQuestion = async (e: React.FormEvent) => {
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
        setQuestion(data.question)
        setHasAnswer(data.has_answer)
        setHasEmail(data.has_email)
        setEmailHint(data.email_hint || "")

        if (data.has_email || data.has_answer) {
          setStep("choose_method")
        } else {
          setErrorMsg(t("forgot_password.error_no_question"))
        }
      } else {
        setErrorMsg(data.error || t("forgot_password.error_generic"))
      }
    } catch {
      setErrorMsg(t("forgot_password.error_generic"))
    } finally {
      setIsLoading(false)
    }
  }

  // ── Send OTP ─────────────────────────────────────────────────────────────
  const sendOtp = async () => {
    setErrorMsg(null)
    setIsLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/accounts/forgot-password/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ action: "request_otp", username: username.trim() }),
      })
      const data = await res.json()
      if (data.success) {
        setEmailHint(data.email_hint || emailHint)
        setResendCooldown(60)
        setStep("otp")
      } else if (data.too_soon) {
        setErrorMsg(t("forgot_password.error_too_soon").replace("{n}", String(data.wait_seconds)))
        setResendCooldown(data.wait_seconds)
        setStep("otp")
      } else {
        setErrorMsg(data.error || t("forgot_password.error_generic"))
      }
    } catch {
      setErrorMsg(t("forgot_password.error_generic"))
    } finally {
      setIsLoading(false)
    }
  }

  // ── Verify OTP + set password ─────────────────────────────────────────────
  const verifyOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)
    const otp = otpDigits.join("")
    if (otp.length < 6) {
      setErrorMsg(t("forgot_password.error_otp_invalid"))
      return
    }
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
        body: JSON.stringify({ action: "verify_otp", username: username.trim(), otp, new_password: newPassword }),
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

  // ── Security question reset ───────────────────────────────────────────────
  const resetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)
    if (newPassword.length < 8) { setErrorMsg(t("forgot_password.error_weak_password")); return }
    if (newPassword !== confirmPassword) { setErrorMsg(t("forgot_password.error_password_mismatch")); return }
    setIsLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/accounts/forgot-password/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ action: "reset_password", username: username.trim(), answer: answer.trim(), new_password: newPassword }),
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

  // ── OTP digit input handler ───────────────────────────────────────────────
  const handleOtpChange = (index: number, value: string) => {
    const digit = value.replace(/\D/g, "").slice(-1)
    const next = [...otpDigits]
    next[index] = digit
    setOtpDigits(next)
    if (digit && index < 5) otpRefs.current[index + 1]?.focus()
  }

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otpDigits[index] && index > 0) {
      otpRefs.current[index - 1]?.focus()
    }
  }

  const stepTitles: Partial<Record<Step, string>> = {
    username:      t("forgot_password.title"),
    choose_method: t("forgot_password.choose_method_title"),
    otp:           t("forgot_password.enter_otp_label"),
    set_password:  t("forgot_password.set_new_password"),
    answer:        t("forgot_password.title"),
    done:          t("forgot_password.success_title"),
  }

  return (
    <div className="flex min-h-screen">
      {/* Left Panel */}
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
          <p className="mt-4 text-lg text-sidebar-foreground/70">{t("forgot_password.brand_description")}</p>
          <div className="mt-10 rounded-xl border border-sidebar-border bg-sidebar-accent/50 p-5">
            <Shield className="mb-3 h-6 w-6 text-primary" />
            <h3 className="font-medium text-sidebar-foreground">{t("forgot_password.security_hint_title")}</h3>
            <p className="mt-1 text-sm text-sidebar-foreground/60">{t("forgot_password.security_hint_desc")}</p>
          </div>
        </div>
        <p className="text-sm text-sidebar-foreground/50">{t("auth.footer_empower")}</p>
      </div>

      {/* Right Panel */}
      <div className="flex flex-1 flex-col">
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
              <h2 className="text-2xl font-bold tracking-tight">{stepTitles[step]}</h2>
              <p className="mt-2 text-muted-foreground">
                {step === "username" && t("forgot_password.username_subtitle")}
                {step === "choose_method" && t("forgot_password.choose_method_subtitle")}
                {step === "otp" && t("forgot_password.otp_sent_message").replace("{email}", emailHint)}
                {step === "set_password" && t("forgot_password.set_new_password_subtitle")}
                {step === "answer" && t("forgot_password.answer_subtitle")}
                {step === "done" && t("forgot_password.success_message")}
              </p>
            </div>

            {errorMsg && (
              <div className="mb-5 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {errorMsg}
              </div>
            )}

            {/* ── Step: username ── */}
            {step === "username" && (
              <form onSubmit={requestQuestion} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="username">{t("auth.username")}</Label>
                  <Input id="username" placeholder={t("auth.username_placeholder")} required
                    value={username} onChange={e => setUsername(e.target.value)} className="h-11 bg-input" />
                </div>
                <Button type="submit" className="h-11 w-full gap-2" disabled={isLoading}>
                  {isLoading
                    ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                    : <>{t("forgot_password.continue_button")}<ArrowRight className="h-4 w-4" /></>}
                </Button>
              </form>
            )}

            {/* ── Step: choose method ── */}
            {step === "choose_method" && (
              <div className="space-y-3">
                {hasEmail && (
                  <Button className="h-14 w-full justify-start gap-3 text-left" onClick={sendOtp} disabled={isLoading}>
                    <Mail className="h-5 w-5 shrink-0" />
                    <div>
                      <p className="font-medium">{t("forgot_password.send_otp_button")}</p>
                      <p className="text-xs opacity-75">{emailHint}</p>
                    </div>
                  </Button>
                )}
                {hasAnswer && (
                  <Button variant="outline" className="h-14 w-full justify-start gap-3 text-left"
                    onClick={() => setStep("answer")} disabled={isLoading}>
                    <HelpCircle className="h-5 w-5 shrink-0" />
                    <p className="font-medium">{t("forgot_password.use_question_button")}</p>
                  </Button>
                )}
                <Button variant="ghost" className="h-11 w-full gap-2"
                  onClick={() => { resetBack(); setStep("username") }}>
                  <ArrowLeft className="h-4 w-4" />{t("forgot_password.back_button")}
                </Button>
              </div>
            )}

            {/* ── Step: enter OTP ── */}
            {step === "otp" && (
              <form onSubmit={(e) => { e.preventDefault(); setStep("set_password") }} className="space-y-6">
                <div className="space-y-3">
                  <Label>{t("forgot_password.enter_otp_label")}</Label>
                  <div className="flex gap-2 justify-between">
                    {otpDigits.map((digit, i) => (
                      <Input
                        key={i}
                        ref={el => { otpRefs.current[i] = el }}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        value={digit}
                        onChange={e => handleOtpChange(i, e.target.value)}
                        onKeyDown={e => handleOtpKeyDown(i, e)}
                        className="h-12 w-12 text-center text-lg font-bold p-0"
                      />
                    ))}
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">
                    {resendCooldown > 0
                      ? t("forgot_password.resend_in").replace("{n}", String(resendCooldown))
                      : ""}
                  </span>
                  <Button type="button" variant="link" className="h-auto p-0 text-sm"
                    disabled={resendCooldown > 0 || isLoading} onClick={sendOtp}>
                    {t("forgot_password.resend_otp")}
                  </Button>
                </div>

                <Button type="submit" className="h-11 w-full gap-2"
                  disabled={otpDigits.join("").length < 6}>
                  {t("forgot_password.verify_otp_button")}<ArrowRight className="h-4 w-4" />
                </Button>
                <Button type="button" variant="ghost" className="h-11 w-full gap-2"
                  onClick={() => { resetBack(); setStep(hasAnswer && hasEmail ? "choose_method" : "username") }}>
                  <ArrowLeft className="h-4 w-4" />{t("forgot_password.back_button")}
                </Button>
              </form>
            )}

            {/* ── Step: set password (after OTP verified) ── */}
            {step === "set_password" && (
              <form onSubmit={verifyOtp} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="new_password_otp">{t("forgot_password.new_password_label")}</Label>
                  <div className="relative">
                    <Input id="new_password_otp" type={showPassword ? "text" : "password"}
                      placeholder={t("forgot_password.new_password_placeholder")} required
                      value={newPassword} onChange={e => setNewPassword(e.target.value)}
                      className="h-11 bg-input pr-11" />
                    <Button type="button" variant="ghost" size="icon"
                      className="absolute right-0 top-0 h-11 w-11 text-muted-foreground hover:bg-transparent hover:text-foreground"
                      onClick={() => setShowPassword(!showPassword)}>
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm_password_otp">{t("forgot_password.confirm_password_label")}</Label>
                  <Input id="confirm_password_otp" type={showPassword ? "text" : "password"}
                    placeholder={t("forgot_password.confirm_password_placeholder")} required
                    value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)}
                    className="h-11 bg-input" />
                </div>
                <Button type="submit" className="h-11 w-full gap-2" disabled={isLoading}>
                  {isLoading
                    ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                    : <>{t("forgot_password.reset_button")}<ArrowRight className="h-4 w-4" /></>}
                </Button>
                <Button type="button" variant="ghost" className="h-11 w-full gap-2"
                  onClick={() => { setErrorMsg(null); setStep("otp") }}>
                  <ArrowLeft className="h-4 w-4" />{t("forgot_password.back_button")}
                </Button>
              </form>
            )}

            {/* ── Step: security question ── */}
            {step === "answer" && (
              <form onSubmit={resetPassword} className="space-y-5">
                <div className="space-y-2">
                  <Label>{t("forgot_password.security_question_label")}</Label>
                  <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm">{question}</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="answer">{t("forgot_password.security_answer_label")}</Label>
                  <Input id="answer" placeholder={t("forgot_password.security_answer_placeholder")} required
                    value={answer} onChange={e => setAnswer(e.target.value)} className="h-11 bg-input" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="new_password">{t("forgot_password.new_password_label")}</Label>
                  <div className="relative">
                    <Input id="new_password" type={showPassword ? "text" : "password"}
                      placeholder={t("forgot_password.new_password_placeholder")} required
                      value={newPassword} onChange={e => setNewPassword(e.target.value)}
                      className="h-11 bg-input pr-11" />
                    <Button type="button" variant="ghost" size="icon"
                      className="absolute right-0 top-0 h-11 w-11 text-muted-foreground hover:bg-transparent hover:text-foreground"
                      onClick={() => setShowPassword(!showPassword)}>
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm_password">{t("forgot_password.confirm_password_label")}</Label>
                  <Input id="confirm_password" type={showPassword ? "text" : "password"}
                    placeholder={t("forgot_password.confirm_password_placeholder")} required
                    value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)}
                    className="h-11 bg-input" />
                </div>
                <Button type="submit" className="h-11 w-full gap-2" disabled={isLoading}>
                  {isLoading
                    ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                    : <>{t("forgot_password.reset_button")}<ArrowRight className="h-4 w-4" /></>}
                </Button>
                {hasEmail && (
                  <Button type="button" variant="outline" className="h-11 w-full gap-2"
                    onClick={() => { resetBack(); sendOtp() }}>
                    <Mail className="h-4 w-4" />{t("forgot_password.send_otp_button_short")}
                  </Button>
                )}
                <Button type="button" variant="ghost" className="h-11 w-full gap-2"
                  onClick={() => { resetBack(); setStep(hasEmail && hasAnswer ? "choose_method" : "username") }}>
                  <ArrowLeft className="h-4 w-4" />{t("forgot_password.back_button")}
                </Button>
              </form>
            )}

            {/* ── Step: done ── */}
            {step === "done" && (
              <Button className="h-11 w-full gap-2" onClick={() => router.push("/login")}>
                {t("forgot_password.go_to_login")}<ArrowRight className="h-4 w-4" />
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
