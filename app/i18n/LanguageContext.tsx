"use client"

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react"
import en from "./dictionaries/en.json"
import ha from "./dictionaries/ha.json"
import ig from "./dictionaries/ig.json"
import yo from "./dictionaries/yo.json"

const dictionaries: Record<string, any> = { en, ha, ig, yo }

type LanguageContextType = {
  language: string
  t: (path: string, params?: Record<string, any>) => string
  setLanguage: (lang: string) => void
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState("en")
  const [isMounted, setIsMounted] = useState(false)

  // Load language from localStorage or profile on mount
  useEffect(() => {
    setIsMounted(true)
    const savedLang = localStorage.getItem("preferred_language")
    if (savedLang && ["en", "ha", "ig", "yo"].includes(savedLang)) {
      setLanguageState(savedLang)
      document.documentElement.lang = savedLang
    } else {
      setLanguageState("en")
      document.documentElement.lang = "en"
    }
  }, [])

  const setLanguage = (lang: string) => {
    setLanguageState(lang)
    localStorage.setItem("preferred_language", lang)
    // Update HTML lang attribute
    document.documentElement.lang = lang
  }

  const t = (path: string, params?: Record<string, any>): string => {
    const keys = path.split(".")
    let result = dictionaries[language] || dictionaries["en"]
    
    for (const key of keys) {
      if (result[key] === undefined) {
        // Fallback to English
        let fallback = dictionaries["en"]
        for (const fkey of keys) {
             fallback = fallback[fkey] || path
        }
        result = fallback
        break
      }
      result = result[key]
    }
    
    if (typeof result !== "string") return path

    // Replace placeholders like {name}
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        result = result.replace(`{${key}}`, value.toString())
      })
    }
    
    return result
  }

  if (!isMounted) {
    return null // Or a loading spinner if preferred, but null is safer for simple i18n
  }

  return (
    <LanguageContext.Provider value={{ language, t, setLanguage }}>
      {children}
    </LanguageContext.Provider>
  )
}

export const useTranslation = () => {
  const context = useContext(LanguageContext)
  if (context === undefined) {
    throw new Error("useTranslation must be used within a LanguageProvider")
  }
  return context
}
