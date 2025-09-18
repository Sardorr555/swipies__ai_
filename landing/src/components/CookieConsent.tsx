import { useState, useEffect } from "react";

export function CookieConsent() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Проверяем, было ли уже принято решение о cookies
    const cookieConsent = localStorage.getItem("cookieConsent");
    if (!cookieConsent) {
      setIsVisible(true);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem("cookieConsent", "accepted");
    setIsVisible(false);
  };

  const handleDecline = () => {
    localStorage.setItem("cookieConsent", "declined");
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 animate-in slide-in-from-bottom-4 duration-300">
      <div className="max-w-2xl mx-auto">
        <div className="bg-card border border-border rounded-lg shadow-lg p-4 backdrop-blur-sm">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <div className="flex-1">
              <h3 className="font-semibold text-card-foreground mb-1 text-sm">
                We use cookies
              </h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                We use cookies to enhance your experience on our website. 
                By continuing to use our site, you agree to our cookie policy.
              </p>
            </div>
            <div className="flex gap-2 flex-shrink-0">
              <button
                onClick={handleDecline}
                className="px-3 py-1.5 text-xs font-medium text-foreground bg-background border border-border rounded hover:bg-accent hover:text-accent-foreground transition-colors"
              >
                Decline
              </button>
              <button
                onClick={handleAccept}
                className="px-3 py-1.5 text-xs font-medium text-primary-foreground bg-primary rounded hover:bg-primary/90 transition-colors"
              >
                Accept
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
