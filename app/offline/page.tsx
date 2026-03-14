"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { WifiOff, RefreshCcw } from "lucide-react"

export default function OfflinePage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md border-none shadow-none text-center">
        <CardHeader>
          <div className="flex justify-center mb-6">
            <div className="rounded-full bg-destructive/10 p-6 animate-pulse">
              <WifiOff className="h-12 w-12 text-destructive" />
            </div>
          </div>
          <CardTitle className="text-3xl font-bold">You're Offline</CardTitle>
          <CardDescription className="text-lg">
            It looks like you've lost your internet connection. 
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-muted-foreground">
            FarmBuddy works best when connected, but don't worry! You can still access your cached chats once you're back online.
          </p>
        </CardContent>
        <CardFooter className="flex justify-center">
          <Button 
            variant="default" 
            size="lg" 
            onClick={() => window.location.reload()}
            className="gap-2"
          >
            <RefreshCcw className="h-4 w-4" />
            Try Again
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
