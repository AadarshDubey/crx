import type { Metadata } from "next";
import { Space_Grotesk, Lexend } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Sidebar } from "@/components/layout";
import clsx from "clsx";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: 'swap',
});

const lexend = Lexend({
  subsets: ["latin"],
  variable: "--font-lexend",
  display: 'swap',
});

export const metadata: Metadata = {
  title: "CRX Pipeline - Crypto Sentiment Dashboard",
  description: "Real-time crypto sentiment analysis from Twitter and news sources",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={clsx(
        spaceGrotesk.variable,
        lexend.variable,
        "font-sans bg-background text-text-primary antialiased selection:bg-primary/30"
      )}>
        <Providers>
          <div className="flex min-h-screen bg-background text-text-primary">
            <div className="hidden lg:block">
              <Sidebar />
            </div>
            <main className="flex-1 lg:ml-64 p-4 md:p-6 transition-all duration-300 ease-in-out">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
