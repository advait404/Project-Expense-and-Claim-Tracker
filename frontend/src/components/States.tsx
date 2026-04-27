import { Loader2 } from "lucide-react";

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm">
      <p className="text-destructive font-medium">Something went wrong</p>
      <p className="mt-1 text-muted-foreground">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 inline-flex items-center rounded-md border border-input bg-background px-3 py-1.5 text-xs font-medium hover:bg-accent"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="rounded-md border border-dashed p-10 text-center">
      <p className="font-medium">{title}</p>
      {description && (
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      )}
    </div>
  );
}
