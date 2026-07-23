import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NSE Stock Tracker",
  description: "Private NSE stock tracker",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

