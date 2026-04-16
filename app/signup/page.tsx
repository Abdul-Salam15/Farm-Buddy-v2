"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select"
import { Eye, EyeOff, Sprout, ArrowRight, Check, Users, Shield, MapPin, Ruler, Droplets, Bug, Sprout as Plant } from "lucide-react"
import { useTranslation } from "@/app/i18n/LanguageContext"
import { API_BASE_URL } from "@/lib/config"

const LANGUAGE_CHOICES = [
  { value: 'en', label: 'English' },
  { value: 'ha', label: 'Hausa' },
  { value: 'ig', label: 'Igbo' },
  { value: 'yo', label: 'Yoruba' },
]

export default function SignupPage() {
  const { t } = useTranslation()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [step, setStep] = useState(1)
  const router = useRouter()

  const SOIL_TYPE_CHOICES = [
    { value: 'sandy', label: t('profile.soil_types.sandy') },
    { value: 'loamy', label: t('profile.soil_types.loamy') },
    { value: 'clay', label: t('profile.soil_types.clay') },
    { value: 'silt', label: t('profile.soil_types.silt') },
    { value: 'peaty', label: t('profile.soil_types.peaty') },
    { value: 'chalky', label: t('profile.soil_types.chalky') },
    { value: 'unknown', label: t('profile.soil_types.unknown') },
  ]

  const PH_CHOICES = [
    { value: 'acidic', label: t('profile.ph_levels.acidic') },
    { value: 'neutral', label: t('profile.ph_levels.neutral') },
    { value: 'alkaline', label: t('profile.ph_levels.alkaline') },
    { value: 'unknown', label: t('profile.ph_levels.unknown') },
  ]

  const WATER_CHOICES = [
    { value: 'rainfed', label: t('profile.water_sources.rainfed') },
    { value: 'irrigated', label: t('profile.water_sources.irrigated') },
    { value: 'seasonal', label: t('profile.water_sources.seasonal') },
  ]

  // State for Step 1
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    // Step 2
    preferred_language: 'en',
    first_name: '',
    last_name: '',
    location: '',
    farm_size_acres: '',
    soil_type: 'unknown',
    ph_level: 'unknown',
    water_source: 'rainfed',
    current_crops: '',
    past_crops: '',
    top_pests: '',
    has_livestock: false,
    livestock_types: '',
    security_answer: '',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value } = e.target
    setFormData(prev => ({ ...prev, [id]: value }))
  }

  const handleSelectChange = (name: string, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    
    if (step === 1) {
      if (formData.password !== formData.confirmPassword) {
        alert(t('settings.alert_password_mismatch'))
        return
      }
      
      setIsLoading(true)
      try {
        const response = await fetch(`${API_BASE_URL}/accounts/signup/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify({
            username: formData.username,
            email: formData.email,
            password: formData.password,
            confirmPassword: formData.confirmPassword,
          }),
        })
        
        const data = await response.json()
        if (data.success) {
          setStep(2)
        } else {
          const errorMsg = data.errors ? Object.values(data.errors).flat().join(", ") : "Signup failed"
          alert(errorMsg)
        }
      } catch (error) {
        console.error("Step 1 Signup failed", error)
        alert("Server error. Please try again.")
      } finally {
        setIsLoading(false)
      }
      return
    }

    // Step 2 submission
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/accounts/signup/farm/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          preferred_language: formData.preferred_language,
          first_name: formData.first_name,
          last_name: formData.last_name,
          location: formData.location,
          farm_size_acres: formData.farm_size_acres === '' ? null : formData.farm_size_acres,
          soil_type: formData.soil_type,
          ph_level: formData.ph_level,
          water_source: formData.water_source,
          current_crops: formData.current_crops,
          past_crops: formData.past_crops,
          top_pests: formData.top_pests,
          has_livestock: formData.has_livestock,
          livestock_types: formData.livestock_types,
          security_answer: formData.security_answer,
        }),
      })

      const data = await response.json()
      if (data.success) {
        router.push("/chat")
      } else {
        const errorMsg = data.errors ? Object.values(data.errors).flat().join(", ") : "Profile setup failed"
        alert(errorMsg)
      }
    } catch (error) {
      console.error("Step 2 Signup failed", error)
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
            {step === 1 ? t('auth.create_account') : t('auth.farm_details')}
          </h1>
          <p className="mt-4 text-lg text-sidebar-foreground/70">
            {step === 1 
              ? t('auth.step1_subtitle')
              : t('auth.step2_subtitle')
            }
          </p>
          
          <div className="mt-10 space-y-4">
            <div className="flex items-start gap-4 rounded-xl border border-sidebar-border bg-sidebar-accent/50 p-5">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/20">
                <Users className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h3 className="font-medium text-sidebar-foreground">{t('landing.community_stats')}</h3>
                <p className="mt-1 text-sm text-sidebar-foreground/60">
                  {t('landing.community_subtitle')}
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4 rounded-xl border border-sidebar-border bg-sidebar-accent/50 p-5">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/20">
                <Shield className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h3 className="font-medium text-sidebar-foreground">{t('landing.features.expert.title')}</h3>
                <p className="mt-1 text-sm text-sidebar-foreground/60">
                   {t('landing.features.expert.desc')}
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <p className="text-sm text-sidebar-foreground/50">
          {t('auth.footer_empower')}
        </p>
      </div>

      {/* Right Panel - Signup Form */}
      <div className="flex flex-1 flex-col overflow-y-auto">
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
            {/* Progress Steps */}
            <div className="mb-8">
              <div className="flex items-center gap-3">
                {[1, 2].map((s) => (
                  <div key={s} className="flex items-center gap-3">
                    <div
                      className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-medium transition-colors ${
                        step >= s
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {step > s ? <Check className="h-4 w-4" /> : s}
                    </div>
                    {s < 2 && (
                      <div
                        className={`h-0.5 w-10 transition-colors ${
                          step > s ? "bg-primary" : "bg-border"
                        }`}
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-2xl font-bold tracking-tight text-foreground">
                {step === 1 ? t('auth.create_account') : t('auth.farm_details')}
              </h2>
              <p className="mt-2 text-muted-foreground">
                {step === 1
                  ? t('auth.step1_subtitle')
                  : t('auth.step2_subtitle')}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5 pb-10">
              {step === 1 ? (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="username" className="text-sm font-medium">
                      {t('auth.username')}
                    </Label>
                    <Input
                      id="username"
                      placeholder={t('auth.username_placeholder')}
                      required
                      value={formData.username}
                      onChange={handleChange}
                      className="h-11 bg-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-sm font-medium">
                      {t('auth.email')}
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder={t('auth.email_placeholder')}
                      required
                      value={formData.email}
                      onChange={handleChange}
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
                        placeholder={t('auth.create_password_placeholder')}
                        required
                        value={formData.password}
                        onChange={handleChange}
                        className="h-11 bg-input pr-11"
                      />
                      <button
                        type="button"
                        className="absolute right-0 top-0 h-11 w-11 flex items-center justify-center text-muted-foreground hover:text-foreground"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword" className="text-sm font-medium">
                      {t('auth.confirm_password')}
                    </Label>
                    <div className="relative">
                      <Input
                        id="confirmPassword"
                        type={showConfirmPassword ? "text" : "password"}
                        placeholder={t('auth.confirm_password_placeholder')}
                        required
                        value={formData.confirmPassword}
                        onChange={handleChange}
                        className="h-11 bg-input pr-11"
                      />
                      <button
                        type="button"
                        className="absolute right-0 top-0 h-11 w-11 flex items-center justify-center text-muted-foreground hover:text-foreground"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      >
                        {showConfirmPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="preferred_language" className="text-sm font-medium">
                      {t('profile.lang_pref')}
                    </Label>
                    <Select 
                      value={formData.preferred_language} 
                      onValueChange={(val) => handleSelectChange('preferred_language', val)}
                    >
                      <SelectTrigger className="h-11 bg-input">
                        <SelectValue placeholder="Select language" />
                      </SelectTrigger>
                      <SelectContent>
                        {LANGUAGE_CHOICES.map(c => (
                          <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="first_name" className="text-sm font-medium">
                        {t('profile.first_name')}
                      </Label>
                      <Input
                        id="first_name"
                        placeholder="e.g. Adebayo"
                        required
                        value={formData.first_name}
                        onChange={handleChange}
                        className="h-11 bg-input"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="last_name" className="text-sm font-medium">
                        {t('profile.last_name')}
                      </Label>
                      <Input
                        id="last_name"
                        placeholder="e.g. Smith"
                        required
                        value={formData.last_name}
                        onChange={handleChange}
                        className="h-11 bg-input"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="location" className="text-sm font-medium">
                      {t('profile.farm_location')}
                    </Label>
                    <div className="relative">
                      <Input
                        id="location"
                        placeholder={t('profile.town_state')}
                        required
                        value={formData.location}
                        onChange={handleChange}
                        className="h-11 bg-input pl-10"
                      />
                      <MapPin className="absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="farm_size_acres" className="text-sm font-medium">
                      {t('auth.farm_size')}
                    </Label>
                    <div className="relative">
                      <Input
                        id="farm_size_acres"
                        type="number"
                        placeholder="e.g. 5.5"
                        value={formData.farm_size_acres}
                        onChange={handleChange}
                        className="h-11 bg-input pl-10"
                        step="0.01"
                      />
                      <Ruler className="absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="soil_type" className="text-sm font-medium">
                        {t('profile.soil_appearance')}
                      </Label>
                      <Select 
                        value={formData.soil_type} 
                        onValueChange={(val) => handleSelectChange('soil_type', val)}
                      >
                        <SelectTrigger className="h-11 bg-input text-xs">
                          <SelectValue placeholder="Soil type" />
                        </SelectTrigger>
                        <SelectContent>
                          {SOIL_TYPE_CHOICES.map(c => (
                            <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="ph_level" className="text-sm font-medium">
                        {t('profile.soil_acidity')}
                      </Label>
                      <Select 
                        value={formData.ph_level} 
                        onValueChange={(val) => handleSelectChange('ph_level', val)}
                      >
                        <SelectTrigger className="h-11 bg-input text-xs">
                          <SelectValue placeholder="Soil pH" />
                        </SelectTrigger>
                        <SelectContent>
                          {PH_CHOICES.map(c => (
                            <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="water_source" className="text-sm font-medium">
                      {t('auth.watering_method')}
                    </Label>
                    <Select 
                      value={formData.water_source} 
                      onValueChange={(val) => handleSelectChange('water_source', val)}
                    >
                      <SelectTrigger className="h-11 bg-input">
                        <SelectValue placeholder="Select method" />
                      </SelectTrigger>
                      <SelectContent>
                        {WATER_CHOICES.map(c => (
                          <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="current_crops" className="text-sm font-medium">
                      {t('profile.current_crops')}
                    </Label>
                    <div className="relative">
                      <Input
                        id="current_crops"
                        placeholder="e.g. maize, cassava (comma separated)"
                        value={formData.current_crops}
                        onChange={handleChange}
                        className="h-11 bg-input pl-10"
                      />
                      <Plant className="absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="past_crops" className="text-sm font-medium">
                      {t('profile.previous_crops')}
                    </Label>
                    <Input
                      id="past_crops"
                      placeholder="What have you grown before?"
                      value={formData.past_crops}
                      onChange={handleChange}
                      className="h-11 bg-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="top_pests" className="text-sm font-medium">
                      {t('profile.main_pests')}
                    </Label>
                    <div className="relative">
                      <Input
                        id="top_pests"
                        placeholder="e.g. armyworms, aphids"
                        value={formData.top_pests}
                        onChange={handleChange}
                        className="h-11 bg-input pl-10"
                      />
                      <Bug className="absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="security_answer" className="text-sm font-medium">
                      Security Question: What is the name of your grandfather?
                    </Label>
                    <Input
                      id="security_answer"
                      placeholder="Used for password recovery"
                      required
                      value={formData.security_answer}
                      onChange={handleChange}
                      className="h-11 bg-input"
                    />
                    <p className="text-xs text-muted-foreground">This is used to recover your account if you forget your password.</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="has_livestock" className="text-sm font-medium">
                        {t('auth.keep_animals')}
                      </Label>
                      <Select 
                        value={formData.has_livestock ? "true" : "false"} 
                        onValueChange={(val) => handleSelectChange('has_livestock', val === "true")}
                      >
                        <SelectTrigger className="h-11 bg-input text-xs">
                          <SelectValue placeholder="Select" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="true">{t('profile.livestock_options.yes')}</SelectItem>
                          <SelectItem value="false">{t('profile.livestock_options.no')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    {formData.has_livestock && (
                      <div className="space-y-2">
                        <Label htmlFor="livestock_types" className="text-sm font-medium">
                          {t('auth.what_kinds')}
                        </Label>
                        <Input
                          id="livestock_types"
                          placeholder="e.g. goats"
                          value={formData.livestock_types}
                          onChange={handleChange}
                          className="h-11 bg-input"
                        />
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="flex gap-3 pt-6">
                {step === 2 && (
                  <Button
                    type="button"
                    variant="outline"
                    className="h-11 flex-1"
                    onClick={() => setStep(1)}
                  >
                    {t('auth.back')}
                  </Button>
                )}
                <Button
                  type="submit"
                  className="h-11 flex-1 gap-2"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                  ) : step === 1 ? (
                    <>
                      {t('auth.continue')}
                      <ArrowRight className="h-4 w-4" />
                    </>
                  ) : (
                    <>
                      {t('auth.create_account')}
                      <Check className="h-4 w-4" />
                    </>
                  )}
                </Button>
              </div>
            </form>

            <p className="mt-8 text-center text-sm text-muted-foreground">
              {t('auth.already_account')}
              <Link
                href="/login"
                className="font-medium text-primary hover:underline"
              >
                {t('auth.signin_link')}
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
