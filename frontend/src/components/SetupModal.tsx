"use client";

import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertCircle, CheckCircle2, Clock } from "lucide-react";

interface SetupStatus {
  ready: boolean;
  components: Record<string, string>;
  errors: string[];
  brand_name: string;
}

interface SetupModalProps {
  open: boolean;
  onSetupComplete?: () => void;
}

export function SetupModal({ open, onSetupComplete }: SetupModalProps) {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    if (!open) return;

    const fetchStatus = async () => {
      try {
        const response = await fetch("/api/v1/admin/setup-status");
        const data = await response.json();
        setStatus(data);
        setLoading(false);
      } catch (error) {
        console.error("Failed to fetch setup status:", error);
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [open, retryCount]);

  const getComponentIcon = (value: string) => {
    if (value === "healthy" || value === "loaded" || value === "configured") {
      return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    }
    if (value === "unconfigured" || value === "missing") {
      return <AlertCircle className="w-4 h-4 text-yellow-500" />;
    }
    if (value === "unhealthy") {
      return <AlertCircle className="w-4 h-4 text-red-500" />;
    }
    return <Clock className="w-4 h-4 text-gray-500" />;
  };

  const formatComponentName = (key: string): string => {
    return key
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  return (
    <Dialog open={open && !status?.ready}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>System Setup Required</DialogTitle>
          <DialogDescription>
            Please wait for all components to be initialized before using the application.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="space-y-4 py-6">
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
              <span className="ml-3">Checking system components...</span>
            </div>
          </div>
        ) : status ? (
          <div className="space-y-6 py-4">
            <div className="space-y-3">
              <h3 className="text-sm font-semibold">Component Status:</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(status.components).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <span className="text-sm font-medium">
                      {formatComponentName(key)}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500 capitalize">
                        {value}
                      </span>
                      {getComponentIcon(value)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {status.errors.length > 0 && (
              <div className="space-y-2 p-4 bg-red-50 dark:bg-red-900/10 rounded-lg border border-red-200 dark:border-red-900/30">
                <h3 className="text-sm font-semibold text-red-800 dark:text-red-200">
                  Issues to Resolve:
                </h3>
                <ul className="space-y-1">
                  {status.errors.map((error, idx) => (
                    <li key={idx} className="text-sm text-red-700 dark:text-red-300">
                      • {error}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {!status.ready && (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setRetryCount((prev) => prev + 1)}
                  className="flex-1"
                >
                  Retry Check
                </Button>
                <Button
                  onClick={() => onSetupComplete?.()}
                  className="flex-1"
                  disabled={status.errors.length > 0}
                >
                  Continue Anyway
                </Button>
              </div>
            )}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
