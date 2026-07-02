import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import { Sidebar } from "@/components/layout/Sidebar";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "mSignals — Multi-Agent Patient State Alignment for Acute Care",
  description: "ICU continuous patient state alignment using the ALI Multi-Agent Signals (MAS) platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${outfit.variable} bg-background text-foreground antialiased min-h-screen flex font-sans`}>
        <Sidebar />
        <main className="flex-1 overflow-y-auto h-screen bg-[#050b14]/10">
          {children}
        </main>
      </body>
    </html>
  );
}
