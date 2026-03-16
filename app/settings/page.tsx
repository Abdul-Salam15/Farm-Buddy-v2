"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Header } from "@/components/header"
import {
  ArrowLeft,
  User,
  Lock,
  Eye,
  EyeOff,
  Save,
  Globe,
  Shield,
  LogOut,
} from "lucide-react"
import { useTranslation } from "@/app/i18n/LanguageContext"

export default function SettingsPage() {
  const { t, setLanguage } = useTranslation()
  const [settingsData, setSettingsData] = useState({
    first_name: "",
    last_name: "",
    preferred_language: "en",
  })
  const [passwordData, setPasswordData] = useState({
    old_password: "",
    new_password: "",
    confirm_password: "",
  })

  const [showOldPassword, setShowOldPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isProfileLoading, setIsProfileLoading] = useState(false)
  const [isPasswordLoading, setIsPasswordLoading] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const router = useRouter()

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await fetch("http://localhost:8000/accounts/settings/", {
          credentials: "include",
          headers: { "Accept": "application/json" }
        })
        const data = await response.json()
        if (data.success) {
          setSettingsData({
            first_name: data.user.first_name,
            last_name: data.user.last_name,
            preferred_language: data.user.preferred_language
          })
          if (data.user.preferred_language) {
            setLanguage(data.user.preferred_language)
          }
        } else {
          router.push("/login")
        }
      } catch (error) {
        console.error("Failed to fetch settings", error)
      } finally {
        setIsLoading(false)
      }
    }
    fetchSettings()
  }, [router, setLanguage])

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsProfileLoading(true)
    try {
      const response = await fetch("http://localhost:8000/accounts/settings/", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "update_profile",
          ...settingsData
        })
      })
      const data = await response.json()
      if (data.success) {
        if (settingsData.preferred_language) {
          setLanguage(settingsData.preferred_language)
        }
        alert(t('settings.alert_profile_success'))
      } else {
        alert(t('settings.alert_profile_error', { errors: JSON.stringify(data.errors || data.error) }))
      }
    } catch (error) {
      console.error("Profile save failed", error)
      alert(t('settings.alert_profile_failed'))
    } finally {
      setIsProfileLoading(false)
    }
  }

  const handlePasswordSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (passwordData.new_password !== passwordData.confirm_password) {
      alert(t('settings.alert_password_mismatch'))
      return
    }
    setIsPasswordLoading(true)
    try {
      const response = await fetch("http://localhost:8000/accounts/settings/", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "change_password",
          old_password: passwordData.old_password,
          new_password1: passwordData.new_password,
          new_password2: passwordData.confirm_password
        })
      })
      const data = await response.json()
      if (data.success) {
        alert(t('settings.alert_password_success'))
        setPasswordData({ old_password: "", new_password: "", confirm_password: "" })
      } else {
        alert(t('settings.alert_profile_error', { errors: JSON.stringify(data.errors || data.error) }))
      }
    } catch (error) {
      console.error("Password change failed", error)
      alert(t('settings.alert_password_failed'))
    } finally {
      setIsPasswordLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Header isAuthenticated />

      <main className="container mx-auto px-4 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <Link
            href="/chat"
            className="mb-4 inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            {t('settings.back_to_chat')}
          </Link>
          <h1 className="text-2xl font-bold">{t('settings.title')}</h1>
          <p className="mt-1 text-muted-foreground">
            {t('settings.subtitle')}
          </p>
        </div>

        <div className="mx-auto max-w-2xl space-y-8">
          {/* General Settings */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <User className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle>{t('settings.general_settings')}</CardTitle>
                  <CardDescription>
                    {t('settings.manage_profile')}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleProfileSave} className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="first_name">{t('settings.first_name')}</Label>
                    <Input
                      id="first_name"
                      placeholder={t('settings.first_name_placeholder')}
                      value={settingsData.first_name}
                      onChange={(e) => setSettingsData({ ...settingsData, first_name: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last_name">{t('settings.last_name')}</Label>
                    <Input
                      id="last_name"
                      placeholder={t('settings.last_name_placeholder')}
                      value={settingsData.last_name}
                      onChange={(e) => setSettingsData({ ...settingsData, last_name: e.target.value })}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="defaultLanguage" className="flex items-center gap-2">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                    {t('settings.default_language')}
                  </Label>
                  <Select 
                    value={settingsData.preferred_language}
                    onValueChange={async (value) => {
                      setSettingsData({ ...settingsData, preferred_language: value })
                      try {
                        await fetch("http://localhost:8000/accounts/update-language/", {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          credentials: "include",
                          body: JSON.stringify({ language: value }),
                        })
                      } catch (error) {
                        console.error("Failed to sync language immediately", error)
                      }
                    }}
                  >
                    <SelectTrigger id="defaultLanguage">
                      <SelectValue placeholder={t('settings.default_language')} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="ha">Hausa</SelectItem>
                      <SelectItem value="ig">Igbo</SelectItem>
                      <SelectItem value="yo">Yoruba</SelectItem>

                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    {t('settings.language_update_hint')}
                  </p>
                </div>

                <Button type="submit" className="gap-2" disabled={isProfileLoading}>
                  {isProfileLoading ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      {t('settings.save_profile')}
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Change Password */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-destructive/10">
                  <Lock className="h-5 w-5 text-destructive" />
                </div>
                <div>
                  <CardTitle>{t('settings.change_password')}</CardTitle>
                  <CardDescription>
                    {t('settings.update_password_desc')}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <form onSubmit={handlePasswordSave} className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="oldPassword">{t('settings.old_password')}</Label>
                  <div className="relative">
                    <Input
                      id="oldPassword"
                      type={showOldPassword ? "text" : "password"}
                      placeholder={t('settings.old_password_placeholder')}
                      className="pr-11"
                      value={passwordData.old_password}
                      onChange={(e) => setPasswordData({ ...passwordData, old_password: e.target.value })}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-full w-11 text-muted-foreground hover:bg-transparent hover:text-foreground"
                      onClick={() => setShowOldPassword(!showOldPassword)}
                    >
                      {showOldPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="newPassword">{t('settings.new_password')}</Label>
                  <div className="relative">
                    <Input
                      id="newPassword"
                      type={showNewPassword ? "text" : "password"}
                      placeholder={t('settings.new_password_placeholder')}
                      className="pr-11"
                      value={passwordData.new_password}
                      onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-full w-11 text-muted-foreground hover:bg-transparent hover:text-foreground"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                    >
                      {showNewPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">{t('settings.confirm_password')}</Label>
                  <div className="relative">
                    <Input
                      id="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      placeholder={t('settings.confirm_password_placeholder')}
                      className="pr-11"
                      value={passwordData.confirm_password}
                      onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-full w-11 text-muted-foreground hover:bg-transparent hover:text-foreground"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>

                <Button type="submit" variant="destructive" className="gap-2" disabled={isPasswordLoading}>
                  {isPasswordLoading ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-destructive-foreground border-t-transparent" />
                  ) : (
                    <>
                      <Shield className="h-4 w-4" />
                      {t('settings.update_password_button')}
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Danger Zone */}
          <Card className="border-destructive/30">
            <CardHeader>
              <CardTitle className="text-destructive">{t('settings.danger_zone')}</CardTitle>
              <CardDescription>
                {t('settings.destructive_actions')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium">{t('settings.delete_account')}</p>
                  <p className="text-sm text-muted-foreground">
                    {t('settings.delete_account_desc')}
                  </p>
                </div>
                <Button variant="outline" className="border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground">
                  {t('settings.delete_account')}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
