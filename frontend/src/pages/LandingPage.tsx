/**
 * LandingPage - Public landing page for Querious
 */
import { useState, useEffect, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { pricingTiers } from "../constants/pricing";
import logo from "../assets/logo.png";
import {
  FileText,
  MessageSquare,
  BookOpen,
  FolderOpen,
  Shield,
  Zap,
  Menu,
  X,
  ArrowRight,
  Upload,
  HelpCircle,
  CheckCircle,
  Github,
  Linkedin,
} from "lucide-react";

// Feature data
const features = [
  {
    icon: FileText,
    title: "Smart Chunking",
    description: "Documents are intelligently split for accurate retrieval",
  },
  {
    icon: MessageSquare,
    title: "Natural Chat",
    description: "Ask questions in plain English, get clear answers",
  },
  {
    icon: BookOpen,
    title: "Source Citations",
    description: "Every answer includes page references you can verify",
  },
  {
    icon: FolderOpen,
    title: "Project Organization",
    description: "Group related documents into searchable projects",
  },
  {
    icon: Shield,
    title: "Secure & Private",
    description: "Your documents are encrypted and never shared",
  },
  {
    icon: Zap,
    title: "Lightning Fast",
    description: "Get answers in seconds, not minutes",
  },
];

// How it works steps
const steps = [
  {
    icon: Upload,
    title: "Upload",
    description: "Drop your PDFs into a chat or project",
  },
  {
    icon: HelpCircle,
    title: "Ask",
    description: "Type your question in natural language",
  },
  {
    icon: CheckCircle,
    title: "Get Answers",
    description: "Receive cited responses instantly",
  },
];

export function LandingPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Track scroll for navbar blur
  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 10);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Scroll-triggered animations
  const observerRef = useRef<IntersectionObserver | null>(null);
  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
          }
        });
      },
      { threshold: 0.1 }
    );

    document.querySelectorAll(".animate-on-scroll").forEach((el) => {
      observerRef.current?.observe(el);
    });

    return () => observerRef.current?.disconnect();
  }, []);

  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
    setMobileMenuOpen(false);
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      {/* ========== NAVBAR ========== */}
      <nav
        className={`fixed top-0 w-full z-50 transition-all duration-300 ${
          isScrolled
            ? "bg-[var(--color-bg)]/80 backdrop-blur-md border-b border-[var(--color-border)]"
            : "bg-transparent"
        }`}
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2">
              <img src={logo} alt="Querious" className="w-8 h-8" />
              <span className="text-xl font-bold text-[var(--color-text-primary)]">
                Querious
              </span>
            </Link>

            {/* Desktop Nav */}
            <div className="hidden md:flex items-center gap-8">
              <button
                onClick={() => scrollToSection("features")}
                className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                Features
              </button>
              <button
                onClick={() => scrollToSection("how-it-works")}
                className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                How it Works
              </button>
              <button
                onClick={() => scrollToSection("pricing")}
                className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                Pricing
              </button>
              {!user && (
                <Link
                  to="/login"
                  className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
                >
                  Log in
                </Link>
              )}
            </div>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 text-[var(--color-text-secondary)]"
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-[var(--color-surface)] border-b border-[var(--color-border)]">
            <div className="px-4 py-4 space-y-3">
              <button
                onClick={() => scrollToSection("features")}
                className="block w-full text-left py-2 text-[var(--color-text-secondary)]"
              >
                Features
              </button>
              <button
                onClick={() => scrollToSection("how-it-works")}
                className="block w-full text-left py-2 text-[var(--color-text-secondary)]"
              >
                How it Works
              </button>
              <button
                onClick={() => scrollToSection("pricing")}
                className="block w-full text-left py-2 text-[var(--color-text-secondary)]"
              >
                Pricing
              </button>
              {!user && (
                <Link
                  to="/login"
                  className="block w-full text-left py-2 text-[var(--color-text-secondary)]"
                >
                  Log in
                </Link>
              )}
            </div>
          </div>
        )}
      </nav>

      {/* ========== HERO SECTION ========== */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="animate-fade-up text-4xl sm:text-5xl lg:text-6xl font-bold text-[var(--color-text-primary)] leading-tight">
            Chat with your documents.
            <br />
            <span className="text-[var(--color-accent)]">
              Get answers instantly.
            </span>
          </h1>
          <p className="animate-fade-up animate-delay-200 mt-6 text-lg sm:text-xl text-[var(--color-text-secondary)] max-w-2xl mx-auto">
            Upload PDFs, ask questions in plain English, and get accurate
            answers with source citations.
          </p>
          <div className="animate-fade-up animate-delay-300 mt-10 flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => navigate(user ? "/home" : "/register")}
              className="btn-primary px-8 py-4 rounded-lg text-lg font-medium flex items-center justify-center gap-2"
            >
              {user ? "Go to Dashboard" : "Get Started Free"}
              <ArrowRight size={20} />
            </button>
            <button
              onClick={() => scrollToSection("how-it-works")}
              className="btn-secondary px-8 py-4 rounded-lg text-lg font-medium"
            >
              See how it works
            </button>
          </div>
        </div>
      </section>

      {/* ========== FEATURES SECTION ========== */}
      <section id="features" className="py-20 px-4 bg-[var(--color-surface)]">
        <div className="max-w-6xl mx-auto">
          <h2 className="animate-on-scroll text-3xl sm:text-4xl font-bold text-center text-[var(--color-text-primary)] mb-16">
            Everything you need to work smarter
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={feature.title}
                className="animate-on-scroll hover-scale p-6 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]"
                style={{ transitionDelay: `${index * 0.1}s` }}
              >
                <feature.icon className="w-10 h-10 text-[var(--color-accent)] mb-4" />
                <h3 className="text-xl font-semibold text-[var(--color-text-primary)] mb-2">
                  {feature.title}
                </h3>
                <p className="text-[var(--color-text-secondary)]">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ========== HOW IT WORKS SECTION ========== */}
      <section id="how-it-works" className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="animate-on-scroll text-3xl sm:text-4xl font-bold text-center text-[var(--color-text-primary)] mb-16">
            How it works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {steps.map((step, index) => (
              <div
                key={step.title}
                className="animate-on-scroll text-center"
                style={{ transitionDelay: `${index * 0.15}s` }}
              >
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-accent-subtle)] flex items-center justify-center">
                  <step.icon className="w-8 h-8 text-[var(--color-accent)]" />
                </div>
                <div className="text-2xl font-bold text-[var(--color-accent)] mb-2">
                  {index + 1}
                </div>
                <h3 className="text-xl font-semibold text-[var(--color-text-primary)] mb-2">
                  {step.title}
                </h3>
                <p className="text-[var(--color-text-secondary)]">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ========== PRICING SECTION ========== */}
      <section id="pricing" className="py-20 px-4 bg-[var(--color-surface)]">
        <div className="max-w-6xl mx-auto">
          <h2 className="animate-on-scroll text-3xl sm:text-4xl font-bold text-center text-[var(--color-text-primary)] mb-4">
            Simple Pricing
          </h2>
          <p className="animate-on-scroll text-center text-[var(--color-text-secondary)] mb-16">
            Start free, upgrade when you need
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {pricingTiers.map((tier, index) => (
              <div
                key={tier.name}
                className={`animate-on-scroll hover-scale relative flex flex-col p-6 rounded-xl border transition-all ${
                  tier.highlighted
                    ? "border-amber-400 dark:border-amber-500 bg-gradient-to-b from-amber-50/50 to-transparent dark:from-amber-900/10"
                    : "border-[var(--color-border)] bg-[var(--color-bg)]"
                }`}
                style={{ transitionDelay: `${index * 0.1}s` }}
              >
                {tier.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-semibold rounded-full">
                    ⭐ {tier.badge}
                  </div>
                )}
                <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-1">
                  {tier.name}
                </h3>
                <div className="mb-4">
                  <span className="text-3xl font-bold text-[var(--color-text-primary)]">
                    {tier.price}
                  </span>
                  <span className="text-[var(--color-text-secondary)] text-sm">
                    {tier.period}
                  </span>
                </div>
                <ul className="flex-1 space-y-2 mb-6">
                  {tier.features.map((feature) => (
                    <li
                      key={feature.text}
                      className="flex items-start gap-2 text-sm text-[var(--color-text-secondary)]"
                    >
                      <span className="text-[var(--color-accent)]">✓</span>
                      {feature.text}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => !tier.comingSoon && navigate("/register")}
                  disabled={tier.comingSoon}
                  className={`w-full py-3 px-4 rounded-lg font-medium text-sm transition-all ${
                    tier.comingSoon
                      ? "bg-[var(--color-border)] text-[var(--color-text-tertiary)] cursor-not-allowed"
                      : tier.highlighted
                      ? "bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white"
                      : "btn-primary"
                  }`}
                >
                  {tier.comingSoon ? "Coming Soon" : "Get Started"}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ========== FOOTER ========== */}
      <footer className="border-t border-[var(--color-border)]">
        {/* Main footer content */}
        <div className="py-12 px-4">
          <div className="max-w-6xl mx-auto">
            <div className="flex flex-col md:flex-row justify-between items-center gap-6">
              <div className="flex items-center gap-2">
                <img src={logo} alt="Querious" className="w-6 h-6" />
                <span className="text-lg font-bold text-[var(--color-text-primary)]">
                  Querious
                </span>
              </div>
              <div className="flex gap-6 text-sm text-[var(--color-text-secondary)]">
                <button
                  onClick={() => scrollToSection("features")}
                  className="hover:text-[var(--color-text-primary)] transition-colors"
                >
                  Features
                </button>
                <button
                  onClick={() => scrollToSection("pricing")}
                  className="hover:text-[var(--color-text-primary)] transition-colors"
                >
                  Pricing
                </button>
                <a
                  href="mailto:support@querious.app"
                  className="hover:text-[var(--color-text-primary)] transition-colors"
                >
                  Contact
                </a>
              </div>
              <p className="text-sm text-[var(--color-text-tertiary)]">
                © 2025 Querious. All rights reserved.
              </p>
            </div>
          </div>
        </div>

        {/* Built by line */}
        <div className="py-3 px-4 border-t border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
          <div className="max-w-6xl mx-auto flex items-center justify-center gap-3 text-xs text-[var(--color-text-tertiary)]">
            <span>Built by</span>
            <span className="font-medium text-[var(--color-text-secondary)]">
              Syed Ali Jaseem
            </span>
            <span className="text-[var(--color-border)]">·</span>
            <a
              href="https://github.com/syedalijaseem"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[var(--color-text-primary)] transition-colors"
            >
              <Github size={14} />
            </a>
            <a
              href="https://linkedin.com/in/syedalijaseem"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[var(--color-text-primary)] transition-colors"
            >
              <Linkedin size={14} />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
