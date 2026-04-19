"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

export interface AppSettings {
  brand_name: string;
  brand_color: string;
  logo_url: string | null;
  favicon_url: string | null;
  page_title: string;
  page_description: string;
  copyright_text: string;
  chat_welcome_message: string;
  chat_placeholder: string;
  enable_suggestions: boolean;
  chat_suggestions: string[];
  theme_mode: string;
  accent_color: string;
  sdk_api_endpoint: string;
  sdk_websocket_endpoint: string | null;
  sdk_auth_type: string;
  enable_knowledge_base: boolean;
  enable_web_search: boolean;
  enable_memory: boolean;
  enable_voice: boolean;
  require_source_approval: boolean;
  auto_approve_sources: boolean;
  max_file_size_mb: number;
}

interface SettingsContextType {
  settings: AppSettings | null;
  loading: boolean;
  error: string | null;
  refreshSettings: () => Promise<void>;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

const DEFAULT_SETTINGS: AppSettings = {
  brand_name: "RAZE",
  brand_color: "#3B82F6",
  logo_url: null,
  favicon_url: null,
  page_title: "RAZE AI - Enterprise Chat",
  page_description: "Enterprise AI Assistant",
  copyright_text: "© 2026 RAZE. All rights reserved.",
  chat_welcome_message: "Hello! I'm RAZE, your AI assistant. How can I help?",
  chat_placeholder: "Ask me anything...",
  enable_suggestions: true,
  chat_suggestions: ["What can you do?", "Tell me about yourself", "Help with this task"],
  theme_mode: "dark",
  accent_color: "#3B82F6",
  sdk_api_endpoint: "http://localhost/api/v1",
  sdk_websocket_endpoint: null,
  sdk_auth_type: "bearer",
  enable_knowledge_base: true,
  enable_web_search: true,
  enable_memory: true,
  enable_voice: false,
  require_source_approval: false,
  auto_approve_sources: true,
  max_file_size_mb: 100,
};

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const response = await fetch("/api/v1/settings");
      if (!response.ok) {
        throw new Error(`Failed to fetch settings: ${response.statusText}`);
      }
      const data = await response.json();
      setSettings(data);
      setError(null);

      // Update document title
      if (data.brand_name) {
        document.title = `${data.brand_name} Dashboard`;
      }
    } catch (err) {
      console.error("Failed to fetch settings:", err);
      setSettings(DEFAULT_SETTINGS);
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  return (
    <SettingsContext.Provider
      value={{
        settings: settings || DEFAULT_SETTINGS,
        loading,
        error,
        refreshSettings: fetchSettings,
      }}
    >
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error("useSettings must be used within SettingsProvider");
  }
  return context;
}
