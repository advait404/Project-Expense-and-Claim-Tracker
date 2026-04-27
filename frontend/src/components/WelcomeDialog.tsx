import { X } from "lucide-react";
import {
  AlertDialog,
  AlertDialogContent,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { welcomeConfig } from "@/config/welcomeConfig";

interface WelcomeDialogProps {
  open: boolean;
  onClose: () => void;
}

export function WelcomeDialog({ open, onClose }: WelcomeDialogProps) {
  return (
    <AlertDialog open={open}>
      <AlertDialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <div className="space-y-6">
          <div className="space-y-2">
            <div className="flex items-start justify-between">
              <h1 className="text-3xl font-bold">{welcomeConfig.title}</h1>
              <button
                onClick={onClose}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <p className="text-muted-foreground">{welcomeConfig.aboutText}</p>
          </div>

          <div className="space-y-3">
            <h2 className="text-lg font-semibold">Key Features</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {welcomeConfig.features.map((feature) => (
                <div
                  key={feature.title}
                  className="rounded-lg border bg-card p-3"
                >
                  <h3 className="font-medium text-sm">{feature.title}</h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Getting Started</h2>
            <div className="space-y-3">
              {welcomeConfig.instructions.map((instruction) => (
                <div
                  key={instruction.step}
                  className="rounded-lg border bg-card p-4"
                >
                  <div className="flex gap-4">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-900 dark:bg-blue-900 dark:text-blue-100 flex-shrink-0">
                      {instruction.step}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold">{instruction.title}</h3>
                      <p className="text-sm text-muted-foreground mt-1">
                        {instruction.description}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <p className="text-sm text-muted-foreground italic">
            {welcomeConfig.closingText}
          </p>

          <div className="flex justify-end">
            <Button onClick={onClose}>Close</Button>
          </div>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
}
