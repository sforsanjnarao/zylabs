import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Project01 Research Copilot",
  description: "AI-powered company research for sales meeting prep.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-muted/30">
        <header className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur">
          <div className="mx-auto flex h-14 w-full max-w-5xl items-center px-5">
            <Link href="/" className="flex items-baseline gap-2 font-semibold">
              <span className="text-lg">
                <span className="text-primary">project</span>01
              </span>
              <span className="text-xs text-muted-foreground">
                Research Copilot
              </span>
            </Link>
          </div>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-5 py-8">
          {children}
        </main>
        <footer className="border-t py-4 text-center text-xs text-muted-foreground">
          Built with FastAPI · LangGraph · Next.js
        </footer>
        <Toaster richColors position="top-center" />
      </body>
    </html>
  );
}
