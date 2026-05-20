import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Frontier",
  description: "Structured multi-objective decision making — Pareto-frontier analysis as a chat",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
