"use client";

import Link from "next/link";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-primary-50 to-white">
      <header className="container mx-auto px-4 py-6 flex items-center justify-between">
        <div className="text-2xl font-bold text-primary-700">ChatCore</div>
        <nav className="flex gap-4">
          <Link href="/auth/login" className="text-sm font-medium hover:text-primary-600">
            Sign In
          </Link>
          <Link
            href="/auth/register"
            className="text-sm font-medium bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"
          >
            Get Started
          </Link>
        </nav>
      </header>

      <main className="container mx-auto px-4 py-20 text-center">
        <h1 className="text-5xl font-bold mb-6">
          AI Chatbot for Your Website
        </h1>
        <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
          Automatically crawl your website, index content, and provide instant AI-powered answers to your visitors.
        </p>
        <Link
          href="/auth/register"
          className="inline-block bg-primary-600 text-white px-8 py-3 rounded-lg text-lg font-medium hover:bg-primary-700"
        >
          Start Free Trial
        </Link>
      </main>
    </div>
  );
}
