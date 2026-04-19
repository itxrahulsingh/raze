"use client";

import { useEffect, useState } from "react";
import { useSettings } from "@/contexts/SettingsContext";
import { SetupModal } from "@/components/SetupModal";

export default function RootLayoutClient({
  children,
}: {
  children: React.ReactNode
}) {
  const { settings } = useSettings();
  const [setupOpen, setSetupOpen] = useState(true);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (settings?.brand_name) {
      document.title = `${settings.brand_name} Admin Dashboard`;
    }
  }, [settings]);

  if (!mounted) {
    return null;
  }

  return (
    <>
      <SetupModal open={setupOpen} onSetupComplete={() => setSetupOpen(false)} />
      {children}
    </>
  );
}
