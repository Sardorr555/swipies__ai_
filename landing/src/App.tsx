import { useState, useEffect } from "react";
import { Header } from "./components/Header";
import { Hero } from "./components/Hero";
import { Features } from "./components/Features";
import { Platforms } from "./components/Platforms";
import { Pricing } from "./components/Pricing";
import { About } from "./components/About";
import { Contact } from "./components/Contact";
import { Footer } from "./components/Footer";
import { Team } from "./components/Team";
import { Careers } from "./components/Careers";
import { Press } from "./components/Press";
import { Partners } from "./components/Partners";
import { CookieConsent } from "./components/CookieConsent";

export default function App() {
  const [isDark, setIsDark] = useState(false);
  const [currentPage, setCurrentPage] = useState("home");

  useEffect(() => {
    // Check for saved theme preference or default to light mode
    const savedTheme = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    
    if (savedTheme === "dark" || (!savedTheme && prefersDark)) {
      setIsDark(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

  const toggleTheme = () => {
    setIsDark(!isDark);
    if (!isDark) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  };

  const handlePageChange = (page: string) => {
    setCurrentPage(page);
    // Scroll to top when changing pages
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const renderPage = () => {
    switch (currentPage) {
      case "team":
        return (
          <>
            <Team />
            <Footer />
          </>
        );
      case "careers":
        return (
          <>
            <Careers />
            <Footer />
          </>
        );
      case "press":
        return (
          <>
            <Press />
            <Footer />
          </>
        );
      case "partners":
        return (
          <>
            <Partners />
            <Footer />
          </>
        );
      case "home":
      default:
        return (
          <main>
            <Hero />
            <Features />
            <Platforms />
            <Pricing />
            <About />
            <Contact />
            <Footer />
          </main>
        );
    }
  };

  return (
    <div className="min-h-screen text-foreground">
      <Header 
        isDark={isDark} 
        toggleTheme={toggleTheme}
        currentPage={currentPage}
        onPageChange={handlePageChange}
      />
      {renderPage()}
      <CookieConsent />
    </div>
  );
}