/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react"

export type NotificationType = {
  id: string
  type: "error" | "success" | "info" | "warning"
  title: string
  message?: string
  duration?: number
  actionLabel?: string
  onAction?: () => void
}

type NotificationInput = Omit<NotificationType, "id"> & { id?: string }

type NotificationContextValue = {
  notifications: NotificationType[]
  addNotification: (notification: NotificationInput) => void
  removeNotification: (id: string) => void
}

const NotificationContext = createContext<NotificationContextValue | null>(null)

const DEFAULT_DURATIONS: Record<NotificationType["type"], number> = {
  success: 5000,
  info: 5000,
  error: 8000,
  warning: 8000,
}

export function NotificationProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const [notifications, setNotifications] = useState<NotificationType[]>([])
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map()
  )

  const removeNotification = useCallback((id: string) => {
    const timer = timersRef.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timersRef.current.delete(id)
    }
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }, [])

  const addNotification = useCallback(
    (input: NotificationInput) => {
      const id = input.id ?? crypto.randomUUID()
      const duration = input.duration ?? DEFAULT_DURATIONS[input.type]
      const notification: NotificationType = { ...input, id, duration }

      setNotifications((prev) => [...prev, notification])

      if (duration > 0) {
        const timer = setTimeout(() => {
          timersRef.current.delete(id)
          setNotifications((prev) => prev.filter((n) => n.id !== id))
        }, duration)
        timersRef.current.set(id, timer)
      }
    },
    []
  )

  // Cleanup all timers on unmount
  useEffect(() => {
    const timers = timersRef.current
    return () => {
      timers.forEach((timer) => clearTimeout(timer))
      timers.clear()
    }
  }, [])

  return (
    <NotificationContext.Provider
      value={{ notifications, addNotification, removeNotification }}
    >
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotifications() {
  const context = useContext(NotificationContext)
  if (!context) {
    throw new Error(
      "useNotifications must be used within a NotificationProvider"
    )
  }
  return context
}
