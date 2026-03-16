"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Header } from "@/components/header"
import {
  Lightbulb,
  ExternalLink,
  Save,
  Cloud,
  Thermometer,
  Droplets,
  Wind,
  Sun,
  LayoutDashboard,
  Settings,
  HelpCircle,
  TrendingUp,
  ArrowLeft,
  Sprout,
  CheckCircle2,
  LogOut,
  MessageCircle
} from "lucide-react"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, CartesianGrid } from "recharts"
import { useTranslation } from "@/app/i18n/LanguageContext"

// Static fallbacks removed - now managed in component state

const chartConfig = {
  temperature: {
    label: "Temperature (°C)",
    color: "var(--chart-4)",
  },
  humidity: {
    label: "Humidity (%)",
    color: "var(--chart-2)",
  },
}

export default function ProfilePage() {
  const { t, setLanguage } = useTranslation()
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [profileData, setProfileData] = useState({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    preferred_language: "en",
    location: "",
    farm_size_acres: "",
    soil_type: "unknown",
    ph_level: "unknown",
    water_source: "rainfed",
    current_crops: "",
    past_crops: "",
    top_pests: "",
    has_livestock: false,
    livestock_types: "",
    telegram_link_token: "",
    daily_tip: "Loading tips...",
  })
  const [weatherData, setWeatherData] = useState<any[]>([])
  const [isWeatherLoading, setIsWeatherLoading] = useState(false)
  const [weatherError, setWeatherError] = useState<string | null>(null)
  const router = useRouter()

  const fetchWeather = async (location: string) => {
    if (!location) return
    setIsWeatherLoading(true)
    setWeatherError(null)

    // OpenWeather city search works best with just the city name
    const cityName = location.split(',')[0].trim()

    try {
      const response = await fetch("http://localhost:8000/chat/api/weather/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ city: cityName }),
      })
      const data = await response.json()
      if (data.success && data.data?.forecast?.list) {
        // Group by day and calculate averages
        const dailyData: Record<string, { temp: number[]; hum: number[] }> = {}
        data.data.forecast.list.forEach((item: any) => {
          const date = new Date(item.dt * 1000)
          const dayName = date.toLocaleDateString('en-US', { weekday: 'short' })
          if (!dailyData[dayName]) dailyData[dayName] = { temp: [], hum: [] }
          dailyData[dayName].temp.push(item.main.temp)
          dailyData[dayName].hum.push(item.main.humidity)
        })

        const formatted = Object.entries(dailyData).map(([day, values]) => ({
          day,
          temperature: Math.round(values.temp.reduce((a, b) => a + b, 0) / values.temp.length),
          humidity: Math.round(values.hum.reduce((a, b) => a + b, 0) / values.hum.length),
        }))
        setWeatherData(formatted)
      } else {
        setWeatherError(data.error || "Could not fetch weather data")
        setWeatherData([])
      }
    } catch (error) {
      console.error("Weather fetch failed", error)
      setWeatherError("Failed to connect to weather service")
    } finally {
      setIsWeatherLoading(false)
    }
  }

  useEffect(() => {
    const fetchProfile = async () => {
      setIsLoading(true)
      try {
        const response = await fetch("http://localhost:8000/accounts/profile/", {
          headers: {
            "Accept": "application/json",
          },
          credentials: "include",
        })
        const data = await response.json()
        if (data.success) {
          const profile = data.profile
          setProfileData({
            ...profile,
            soil_type: profile.soil_type || "unknown",
            ph_level: profile.ph_level || "unknown",
          })
          if (profile.preferred_language) {
            setLanguage(profile.preferred_language)
          }
          if (profile.location) {
            fetchWeather(profile.location)
          }
        } else {
          router.push("/login")
        }
      } catch (error) {
        console.error("Failed to fetch profile", error)
      } finally {
        setIsLoading(false)
      }
    }
    fetchProfile()
  }, [router, setLanguage])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { id, value } = e.target
    setProfileData(prev => ({ ...prev, [id]: value }))
  }

  const handleSelectChange = async (id: string, value: string | boolean) => {
    setProfileData(prev => ({ ...prev, [id]: value }))
    
    // Immediate sync for language
    if (id === 'preferred_language' && typeof value === 'string') {
      setLanguage(value)
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
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    try {
      const response = await fetch("http://localhost:8000/accounts/profile/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(profileData),
      })
      const data = await response.json()
      if (data.success) {
        alert(t('profile.alert_success'))
        fetchWeather(profileData.location)
      } else {
        alert(t('profile.alert_error', { errors: JSON.stringify(data.errors) }))
      }
    } catch (error) {
      console.error("Save failed", error)
      alert(t('profile.alert_save_failed'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleLogout = async () => {
    try {
      await fetch("http://localhost:8000/accounts/logout/", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })
      window.location.href = "/login"
    } catch (err) {
      console.error("Logout failed", err)
      window.location.href = "/login"
    }
  }

  const handleOpenTelegram = () => {
    const botUsername = "FarmBuddyAI_Bot" // This should ideally come from env/config
    const token = profileData.telegram_link_token
    if (token) {
      window.open(`https://t.me/${botUsername}?start=${token}`, '_blank')
    } else {
      alert(t('profile.alert_no_token'))
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
          <button
            onClick={handleLogout}
            className="mb-4 inline-flex items-center gap-2 text-sm text-red-400 transition-colors hover:text-red-500"
          >
            <LogOut className="h-4 w-4" />
            {t('common.logout')}
          </button>
          <h1 className="text-2xl font-bold">{t('profile.title')}</h1>
          <p className="mt-1 text-muted-foreground">
            {t('profile.subtitle')}
          </p>
        </div>

        {/* Quick Action Cards */}
        <div className="mb-8 grid gap-4 sm:grid-cols-2">
          <Card className="overflow-hidden border-0 bg-gradient-to-br from-amber-50 to-amber-100/50 dark:from-amber-950/30 dark:to-amber-900/20">
            <CardContent className="flex items-start gap-4 p-5">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-500/20">
                <Lightbulb className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <h3 className="font-semibold text-amber-900 dark:text-amber-100">{t('profile.daily_tip')}</h3>
                <p className="mt-1 text-sm text-amber-800/80 dark:text-amber-200/70">
                  {profileData.daily_tip || t('profile.daily_tip_placeholder')}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="overflow-hidden border-0 bg-gradient-to-br from-sky-50 to-sky-100/50 dark:from-sky-950/30 dark:to-sky-900/20">
            <CardContent className="flex items-start gap-4 p-5">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-sky-500/20">
                <MessageCircle className="h-5 w-5 text-sky-600 dark:text-sky-400" />
              </div>
              <div>
                <h3 className="font-semibold text-sky-900 dark:text-sky-100">{t('profile.stay_connected')}</h3>
                <p className="mt-1 text-sm text-sky-800/80 dark:text-sky-200/70">
                  {t('profile.telegram_advice')}
                </p>
                <Button size="sm" className="mt-3 gap-2 bg-sky-600 hover:bg-sky-700" onClick={handleOpenTelegram}>
                  <ExternalLink className="h-3.5 w-3.5" />
                  {t('profile.open_telegram')}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-8 lg:grid-cols-3">
          {/* Farm Data Form */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <Sprout className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <CardTitle>{t('profile.edit_farm_data')}</CardTitle>
                    <CardDescription>
                      {t('profile.update_info')}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSave} className="space-y-6">
                  {/* Basic Info */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="preferred_language">{t('profile.lang_pref')}</Label>
                      <Select 
                        value={profileData.preferred_language} 
                        onValueChange={(val) => handleSelectChange('preferred_language', val)}
                      >
                        <SelectTrigger id="preferred_language">
                          <SelectValue placeholder={t('profile.lang_pref')} />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="en">English</SelectItem>
                          <SelectItem value="ha">Hausa</SelectItem>
                          <SelectItem value="ig">Igbo</SelectItem>
                          <SelectItem value="yo">Yoruba</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="first_name">{t('profile.first_name')}</Label>
                      <Input id="first_name" value={profileData.first_name} onChange={handleInputChange} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="last_name">{t('profile.last_name')}</Label>
                      <Input id="last_name" value={profileData.last_name} onChange={handleInputChange} />
                    </div>
                  </div>

                  {/* Location */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="location">{t('profile.farm_location')}</Label>
                      <Input
                        id="location"
                        value={profileData.location}
                        onChange={handleInputChange}
                        placeholder={t('profile.town_state')}
                      />
                      <p className="text-xs text-muted-foreground">
                        {t('profile.town_state')}
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="farm_size_acres">{t('profile.farm_size')}</Label>
                      <Input
                        id="farm_size_acres"
                        type="number"
                        value={profileData.farm_size_acres}
                        onChange={handleInputChange}
                        placeholder={t('profile.leave_blank')}
                      />
                    </div>
                  </div>

                  {/* Soil */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="soil_type">{t('profile.soil_appearance')}</Label>
                      <Select 
                        value={profileData.soil_type} 
                        onValueChange={(val) => handleSelectChange('soil_type', val)}
                      >
                        <SelectTrigger id="soil_type">
                          <SelectValue placeholder={t('profile.soil_appearance')} />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="unknown">{t('profile.soil_types.unknown')}</SelectItem>
                          <SelectItem value="sandy">{t('profile.soil_types.sandy')}</SelectItem>
                          <SelectItem value="clay">{t('profile.soil_types.clay')}</SelectItem>
                          <SelectItem value="loamy">{t('profile.soil_types.loamy')}</SelectItem>
                          <SelectItem value="silt">{t('profile.soil_types.silt')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="ph_level">{t('profile.soil_acidity')}</Label>
                      <Select 
                        value={profileData.ph_level} 
                        onValueChange={(val) => handleSelectChange('ph_level', val)}
                      >
                        <SelectTrigger id="ph_level">
                          <SelectValue placeholder={t('profile.soil_acidity')} />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="unknown">{t('profile.ph_levels.unknown')}</SelectItem>
                          <SelectItem value="acidic">{t('profile.ph_levels.acidic')}</SelectItem>
                          <SelectItem value="neutral">{t('profile.ph_levels.neutral')}</SelectItem>
                          <SelectItem value="alkaline">{t('profile.ph_levels.alkaline')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* Irrigation & Crops */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="water_source">{t('profile.irrigation_method')}</Label>
                      <Select 
                        value={profileData.water_source} 
                        onValueChange={(val) => handleSelectChange('water_source', val)}
                      >
                        <SelectTrigger id="water_source">
                          <SelectValue placeholder={t('profile.irrigation_method')} />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="rainfed">{t('profile.water_sources.rainfed')}</SelectItem>
                          <SelectItem value="irrigated">{t('profile.water_sources.irrigated')}</SelectItem>
                          <SelectItem value="seasonal">{t('profile.water_sources.seasonal')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="current_crops">{t('profile.current_crops')}</Label>
                      <Input
                        id="current_crops"
                        value={profileData.current_crops}
                        onChange={handleInputChange}
                        placeholder="e.g. maize, tomatoes, groundnuts"
                      />
                      <p className="text-xs text-muted-foreground">
                        {t('profile.comma_separated')}
                      </p>
                    </div>
                  </div>

                  {/* History */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="past_crops">{t('profile.previous_crops')}</Label>
                      <Input
                        id="past_crops"
                        value={profileData.past_crops}
                        onChange={handleInputChange}
                        placeholder="e.g. cassava, yam"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="top_pests">{t('profile.common_pests')}</Label>
                      <Textarea
                        id="top_pests"
                        value={profileData.top_pests}
                        onChange={handleInputChange}
                        placeholder="e.g. armyworms, aphids"
                        className="min-h-[42px] resize-none"
                        rows={1}
                      />
                    </div>
                  </div>

                  {/* Animals */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="has_livestock">{t('profile.keep_animals')}</Label>
                      <Select 
                        value={profileData.has_livestock ? "yes" : "no"} 
                        onValueChange={(val) => handleSelectChange('has_livestock', val === "yes")}
                      >
                        <SelectTrigger id="has_livestock">
                          <SelectValue placeholder={t('profile.keep_animals')} />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="no">{t('profile.no')}</SelectItem>
                          <SelectItem value="yes">{t('profile.yes')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    {profileData.has_livestock && (
                      <div className="space-y-2">
                        <Label htmlFor="livestock_types">{t('profile.what_animals')}</Label>
                        <Input
                          id="livestock_types"
                          value={profileData.livestock_types}
                          onChange={handleInputChange}
                          placeholder="e.g. goats, chickens"
                        />
                      </div>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="telegram_link_token">Telegram Link Token</Label>
                    <div className="flex gap-2">
                      <Input
                        id="telegram_link_token"
                        value={profileData.telegram_link_token || "Already Linked"}
                        className="font-mono text-sm flex-1"
                        readOnly
                      />
                      <Button 
                        type="button" 
                        variant="outline" 
                        onClick={handleOpenTelegram}
                        disabled={!profileData.telegram_link_token}
                        className="gap-2"
                      >
                        <MessageCircle className="h-4 w-4" />
                        Open Bot
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Use this token to link your account to our Telegram bot for mobile notifications.
                    </p>
                  </div>

                  <Button type="submit" className="w-full gap-2 sm:w-auto" disabled={isSaving}>
                    {isSaving ? (
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                    ) : (
                      <>
                        <Save className="h-4 w-4" />
                        {t('profile.save_farm_data')}
                      </>
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Weather Forecast */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <Cloud className="h-5 w-5 text-primary" />
                  <CardTitle className="text-base">{t('profile.weekly_forecast')}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-4 flex items-center justify-center gap-6">
                  <div className="flex items-center gap-2">
                    <div className="h-2.5 w-2.5 rounded-full bg-chart-4" />
                    <span className="text-xs text-muted-foreground">{t('profile.avg_temp')} (°C)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-2.5 w-2.5 rounded-full bg-chart-2" />
                    <span className="text-xs text-muted-foreground">{t('profile.humidity')} (%)</span>
                  </div>
                </div>

                <div className="h-44 w-full relative">
                  {isWeatherLoading && (
                    <div className="absolute inset-0 z-20 flex items-center justify-center bg-background/50 backdrop-blur-sm">
                      <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    </div>
                  )}
                  {weatherError ? (
                    <div className="flex h-full flex-col items-center justify-center text-sm text-destructive italic border border-destructive/20 rounded-lg p-4 text-center">
                      <p>{weatherError}</p>
                      <p className="text-xs text-muted-foreground mt-1">Try entering just the city name (e.g. "Lagos")</p>
                    </div>
                  ) : weatherData.length === 0 && !isWeatherLoading ? (
                    <div className="flex h-full items-center justify-center text-sm text-muted-foreground italic border rounded-lg">
                      No weather data for this location
                    </div>
                  ) : (
                    <ChartContainer config={chartConfig} className="h-full w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={weatherData}>
                          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                          <XAxis
                            dataKey="day"
                            tick={{ fontSize: 11 }}
                            tickLine={false}
                            axisLine={false}
                          />
                          <YAxis
                            yAxisId="temp"
                            orientation="left"
                            tick={{ fontSize: 11 }}
                            tickLine={false}
                            axisLine={false}
                            domain={['auto', 'auto']}
                          />
                          <YAxis
                            yAxisId="humidity"
                            orientation="right"
                            tick={{ fontSize: 11 }}
                            tickLine={false}
                            axisLine={false}
                            domain={[0, 100]}
                          />
                          <ChartTooltip content={<ChartTooltipContent />} />
                          <Line
                            yAxisId="temp"
                            type="monotone"
                            dataKey="temperature"
                            stroke="var(--chart-4)"
                            strokeWidth={2}
                            dot={{ r: 3, fill: "var(--chart-4)" }}
                          />
                          <Line
                            yAxisId="humidity"
                            type="monotone"
                            dataKey="humidity"
                            stroke="var(--chart-2)"
                            strokeWidth={2}
                            dot={{ r: 3, fill: "var(--chart-2)" }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </ChartContainer>
                  )}
                </div>

                <div className="mt-5 grid grid-cols-3 gap-2">
                  <div className="rounded-xl bg-muted/50 p-3 text-center">
                    <Thermometer className="mx-auto h-4 w-4 text-orange-500" />
                    <p className="mt-1.5 text-lg font-semibold">
                      {weatherData.length > 0 
                        ? `${Math.round(weatherData.reduce((acc, curr) => acc + curr.temperature, 0) / weatherData.length)}°C` 
                        : "--"}
                    </p>
                    <p className="text-xs text-muted-foreground">{t('profile.avg_temp')}</p>
                  </div>
                  <div className="rounded-xl bg-muted/50 p-3 text-center">
                    <Droplets className="mx-auto h-4 w-4 text-blue-500" />
                    <p className="mt-1.5 text-lg font-semibold">
                      {weatherData.length > 0 
                        ? `${Math.round(weatherData.reduce((acc, curr) => acc + curr.humidity, 0) / weatherData.length)}%` 
                        : "--"}
                    </p>
                    <p className="text-xs text-muted-foreground">{t('profile.humidity')}</p>
                  </div>
                  <div className="rounded-xl bg-muted/50 p-3 text-center">
                    <TrendingUp className="mx-auto h-4 w-4 text-primary" />
                    <p className="mt-1.5 text-lg font-semibold">
                      {weatherData.length > 0 ? t('profile.outlook_good') : "--"}
                    </p>
                    <p className="text-xs text-muted-foreground">{t('profile.outlook')}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recent Chat History */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <MessageCircle className="h-5 w-5 text-primary" />
                  <CardTitle className="text-base">{t('profile.recent_chat')}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="rounded-xl bg-muted/30 py-8 text-center">
                  <MessageCircle className="mx-auto h-8 w-8 text-muted-foreground/50" />
                  <p className="mt-3 text-sm text-muted-foreground">
                    {t('profile.no_recent')}
                  </p>
                  <Link href="/chat">
                    <Button variant="link" size="sm" className="mt-1">
                      {t('profile.start_chatting')}
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}
