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

const LANGUAGE_CHOICES = [
  { value: 'en', label: 'English' },
  { value: 'ha', label: 'Hausa' },
  { value: 'ig', label: 'Igbo' },
  { value: 'yo', label: 'Yoruba' },
]

const SOIL_TYPE_CHOICES = [
  { value: 'sandy', label: 'Sandy' },
  { value: 'loamy', label: 'Loamy' },
  { value: 'clay', label: 'Clay' },
  { value: 'silt', label: 'Silty' },
  { value: 'peaty', label: 'Peaty' },
  { value: 'chalky', label: 'Chalky' },
  { value: 'unknown', label: 'I am not sure' },
]

const PH_CHOICES = [
  { value: 'acidic', label: 'Acidic (tastes sour, kills grass)' },
  { value: 'neutral', label: 'Neutral (normal soil)' },
  { value: 'alkaline', label: 'Alkaline (white crust on soil surface)' },
  { value: 'unknown', label: 'I am not sure' },
]

const WATER_CHOICES = [
  { value: 'rainfed', label: 'Rainfed only' },
  { value: 'irrigated', label: 'I have irrigation' },
  { value: 'seasonal', label: 'Seasonal stream / borehole' },
]

export default function SignupPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [step, setStep] = useState(1)
  const router = useRouter()

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
        alert("Passwords do not match!")
        return
      }
      
      setIsLoading(true)
      try {
        const response = await fetch("http://localhost:8000/accounts/signup/", {
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
      const response = await fetch("http://localhost:8000/accounts/signup/farm/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        // We need to send cookies to stay logged in from step 1
        // Fetch does not send cookies by default to different origins
        // We can use credentials: 'include'
        credentials: "include",
        body: JSON.stringify({
          preferred_language: formData.preferred_language,
          first_name: formData.first_name,
          last_name: formData.last_name,
          location: formData.location,
          farm_size_acres: formData.farm_size_acres,
          soil_type: formData.soil_type,
          ph_level: formData.ph_level,
          water_source: formData.water_source,
          current_crops: formData.current_crops,
          past_crops: formData.past_crops,
          top_pests: formData.top_pests,
          has_livestock: formData.has_livestock,
          livestock_types: formData.livestock_types,
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
            {step === 1 ? "Join thousands of farmers" : "About your farming environment"}
          </h1>
          <p className="mt-4 text-lg text-sidebar-foreground/70">
            {step === 1 
              ? "Create your free account and start getting AI-powered agricultural advice tailored to your farm."
              : "This information helps us provide you with the most accurate advice for your specific soil and crops."
            }
          </p>
          
          <div className="mt-10 space-y-4">
            <div className="flex items-start gap-4 rounded-xl border border-sidebar-border bg-sidebar-accent/50 p-5">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/20">
                <Users className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h3 className="font-medium text-sidebar-foreground">Community Driven</h3>
                <p className="mt-1 text-sm text-sidebar-foreground/60">
                  Join a growing community of farmers sharing knowledge and best practices.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4 rounded-xl border border-sidebar-border bg-sidebar-accent/50 p-5">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/20">
                <Shield className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h3 className="font-medium text-sidebar-foreground">Secure & Private</h3>
                <p className="mt-1 text-sm text-sidebar-foreground/60">
                  Your farm data is encrypted and never shared with third parties.
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <p className="text-sm text-sidebar-foreground/50">
          Trusted by 10,000+ farmers across Nigeria
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
                {step === 1 ? "Create your account" : "Farm Details"}
              </h2>
              <p className="mt-2 text-muted-foreground">
                {step === 1
                  ? "Enter your details to get started"
                  : "Final step: About your farming environment"}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5 pb-10">
              {step === 1 ? (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="username" className="text-sm font-medium">
                      Username
                    </Label>
                    <Input
                      id="username"
                      placeholder="Choose a username"
                      required
                      value={formData.username}
                      onChange={handleChange}
                      className="h-11 bg-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-sm font-medium">
                      Email
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="Enter your email address"
                      required
                      value={formData.email}
                      onChange={handleChange}
                      className="h-11 bg-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-sm font-medium">
                      Password
                    </Label>
                    <div className="relative">
                      <Input
                        id="password"
                        type={showPassword ? "text" : "password"}
                        placeholder="Create a password"
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
                      Confirm Password
                    </Label>
                    <div className="relative">
                      <Input
                        id="confirmPassword"
                        type={showConfirmPassword ? "text" : "password"}
                        placeholder="Confirm your password"
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
                      Preferred Language
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
                        First Name
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
                        Last Name
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
                      Farm Location
                    </Label>
                    <div className="relative">
                      <Input
                        id="location"
                        placeholder="Town, State"
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
                      Farm size in acres
                    </Label>
                    <div className="relative">
                      <Input
                        id="farm_size_acres"
                        type="number"
                        placeholder="e.g. 5.5"
                        value={formData.farm_size_acres}
                        onChange={handleChange}
                        className="h-11 bg-input pl-10"
                      />
                      <Ruler className="absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="soil_type" className="text-sm font-medium">
                        Soil appearance
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
                        Soil description
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
                      Crop watering method
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
                      Current crops
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
                      Previous crops
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
                      Top Pests
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

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="has_livestock" className="text-sm font-medium">
                        Keep animals?
                      </Label>
                      <Select 
                        value={formData.has_livestock ? "true" : "false"} 
                        onValueChange={(val) => handleSelectChange('has_livestock', val === "true")}
                      >
                        <SelectTrigger className="h-11 bg-input text-xs">
                          <SelectValue placeholder="Select" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="true">Yes</SelectItem>
                          <SelectItem value="false">No</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    {formData.has_livestock && (
                      <div className="space-y-2">
                        <Label htmlFor="livestock_types" className="text-sm font-medium">
                          What kinds?
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
                    Back
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
                      Continue
                      <ArrowRight className="h-4 w-4" />
                    </>
                  ) : (
                    <>
                      Create Account
                      <Check className="h-4 w-4" />
                    </>
                  )}
                </Button>
              </div>
            </form>

            <p className="mt-8 text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link
                href="/login"
                className="font-medium text-primary hover:underline"
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
