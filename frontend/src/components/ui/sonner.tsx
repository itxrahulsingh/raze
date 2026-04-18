"use client";

import type * as React from "react";
import { Toaster as Sonner } from "sonner";

type ToasterProps = React.ComponentProps<typeof Sonner>;

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      richColors
      closeButton
      position="top-right"
      toastOptions={{
        style: {
          borderRadius: "12px",
        },
      }}
      {...props}
    />
  );
};

export { Toaster };
