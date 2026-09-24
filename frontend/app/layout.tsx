import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({ 
  subsets: ["latin"],
  variable: "--font-inter",
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({ 
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: 'swap',
});

export const metadata: Metadata = {
  title: "RAIN-AI | Regime-Aware Monsoon Rainfall Intelligence",
  description: "AI Post-Processing of Numerical Weather Prediction (NWP) Monsoon Rainfall Forecasts for MoES / NCMRWF — SIH Problem Statement 26080.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable} dark`}>
      <body className="bg-space-950 text-white antialiased font-sans w-full h-full overflow-x-hidden">
        {children}
      </body>
    </html>
  );
}
