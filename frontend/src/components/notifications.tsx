import {
  CheckCircle2,
  AlertCircle,
  Info,
  AlertTriangle,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useNotifications, type NotificationType } from "@/lib/notifications"

const iconMap: Record<
  NotificationType["type"],
  typeof CheckCircle2
> = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
  warning: AlertTriangle,
}

const styleMap: Record<
  NotificationType["type"],
  { container: string; icon: string }
> = {
  success: {
    container: "bg-emerald-950/80 border-emerald-800/60",
    icon: "text-emerald-400",
  },
  error: {
    container: "bg-red-950/80 border-red-800/60",
    icon: "text-red-400",
  },
  info: {
    container: "bg-blue-950/80 border-blue-800/60",
    icon: "text-blue-400",
  },
  warning: {
    container: "bg-amber-950/80 border-amber-800/60",
    icon: "text-amber-400",
  },
}

function NotificationCard({ notification }: { notification: NotificationType }) {
  const { removeNotification } = useNotifications()
  const Icon = iconMap[notification.type]
  const styles = styleMap[notification.type]

  return (
    <div
      className={cn(
        "pointer-events-auto flex w-full max-w-[400px] items-start gap-3 rounded-lg border p-3 shadow-lg backdrop-blur-sm animate-slide-in-right",
        styles.container
      )}
      role="alert"
    >
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", styles.icon)} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-100">
          {notification.title}
        </p>
        {notification.message && (
          <p className="mt-0.5 text-xs text-zinc-400 leading-relaxed">
            {notification.message}
          </p>
        )}
        {notification.actionLabel && notification.onAction && (
          <button
            onClick={() => {
              removeNotification(notification.id)
              notification.onAction!()
            }}
            className="mt-1.5 rounded bg-zinc-700/60 px-2.5 py-1 text-xs font-medium text-zinc-200 transition-colors hover:bg-zinc-600/60"
          >
            {notification.actionLabel}
          </button>
        )}
      </div>
      <button
        onClick={() => removeNotification(notification.id)}
        className="shrink-0 rounded p-0.5 text-zinc-500 transition-colors hover:text-zinc-300 hover:bg-zinc-800/50"
        aria-label="Dismiss notification"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

export function NotificationDisplay() {
  const { notifications } = useNotifications()

  if (notifications.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      {notifications.map((notification) => (
        <NotificationCard key={notification.id} notification={notification} />
      ))}
    </div>
  )
}
