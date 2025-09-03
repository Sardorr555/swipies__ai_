import { useState } from "react";
import { Button } from "./ui/button";
import { Sheet, SheetContent, SheetTrigger } from "./ui/sheet";
import { Moon, Sun, Menu, Bot, ChevronDown } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "./ui/dropdown-menu";

interface HeaderProps {
  isDark: boolean;
  toggleTheme: () => void;
  currentPage: string;
  onPageChange: (page: string) => void;
}

const RAGFLOW_URL = "https://ragflow.yourdomain.tld";


export function Header({ isDark, toggleTheme, currentPage, onPageChange }: HeaderProps) {
  const [isOpen, setIsOpen] = useState(false);

  const navigation = [
    { name: "Home", href: "home" },
    { name: "Features", href: "features" },
    { name: "Pricing", href: "pricing" }
  ];

  const companyPages = [
    { name: "About", href: "about" },
    //{ name: "Team", href: "team" },
   // { name: "Careers", href: "careers" },
    //{ name: "Press", href: "press" },
    { name: "Partners", href: "partners" }
  ];

  const handleNavClick = (href: string) => {
    if (["home", "team", "careers", "press", "partners"].includes(href)) {
      onPageChange(href);
    } else {
      onPageChange("home");
      // For sections on the home page, scroll to them after a brief delay
      setTimeout(() => {
        const element = document.getElementById(href);
        if (element) {
          element.scrollIntoView({ behavior: "smooth" });
        }
      }, 100);
    }
    setIsOpen(false);
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-card/95 backdrop-blur-sm border-b border-border">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <div 
          className="flex items-center space-x-2 cursor-pointer" 
          onClick={() => onPageChange("home")}
        >
          <Bot className="h-8 w-8 text-primary" />
          <span className="text-xl font-bold">Swipies AI</span>
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center space-x-8">
          {navigation.map((item) => (
            <button
              key={item.name}
              onClick={() => handleNavClick(item.href)}
              className={`text-sm font-medium transition-colors hover:text-primary ${
                (currentPage === item.href || 
                 (currentPage === "home" && ["features", "pricing"].includes(item.href)))
                  ? "text-primary" 
                  : "text-muted-foreground"
              }`}
            >
              {item.name}
            </button>
          ))}
          
          {/* Company Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className={`flex items-center gap-1 text-sm font-medium transition-colors hover:text-primary ${
                companyPages.some(page => page.href === currentPage) || 
                (currentPage === "home" && "about" === "about")
                  ? "text-primary" 
                  : "text-muted-foreground"
              }`}>
                Company
                <ChevronDown className="h-3 w-3" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-40">
              {companyPages.map((item) => (
                <DropdownMenuItem 
                  key={item.name}
                  onClick={() => handleNavClick(item.href)}
                  className="cursor-pointer"
                >
                  {item.name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <button
            onClick={() => handleNavClick("contact")}
            className={`text-sm font-medium transition-colors hover:text-primary ${
              (currentPage === "home" && "contact" === "contact")
                ? "text-primary" 
                : "text-muted-foreground"
            }`}
          >
            Contact
          </button>
        </nav>

        {/* Desktop Actions */}
        <div className="hidden md:flex items-center space-x-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleTheme}
            className="h-9 w-9 p-0"
          >
            {isDark ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>

          <Button size="sm" onClick={() => window.location.href = RAGFLOW_URL}>
          Get Started
         </Button>
        </div>

        {/* Mobile Menu */}
        <div className="md:hidden flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleTheme}
            className="h-9 w-9 p-0"
          >
            {isDark ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>
          
          <Sheet open={isOpen} onOpenChange={setIsOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="sm" className="h-9 w-9 p-0">
                <Menu className="h-4 w-4" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-72">
              <div className="flex flex-col space-y-4 mt-8">
                {navigation.map((item) => (
                  <button
                    key={item.name}
                    onClick={() => handleNavClick(item.href)}
                    className={`text-left py-2 text-sm font-medium transition-colors hover:text-primary ${
                      (currentPage === item.href || 
                       (currentPage === "home" && ["features", "pricing"].includes(item.href)))
                        ? "text-primary" 
                        : "text-muted-foreground"
                    }`}
                  >
                    {item.name}
                  </button>
                ))}
                
                <div className="py-2">
                  <div className="text-sm font-medium text-muted-foreground mb-2">Company</div>
                  <div className="pl-4 space-y-2">
                    {companyPages.map((item) => (
                      <button
                        key={item.name}
                        onClick={() => handleNavClick(item.href)}
                        className={`block text-left py-1 text-sm transition-colors hover:text-primary ${
                          currentPage === item.href ? "text-primary" : "text-muted-foreground"
                        }`}
                      >
                        {item.name}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  onClick={() => handleNavClick("contact")}
                  className={`text-left py-2 text-sm font-medium transition-colors hover:text-primary ${
                    (currentPage === "home" && "contact" === "contact")
                      ? "text-primary" 
                      : "text-muted-foreground"
                  }`}
                >
                  Contact
                </button>
                
                
                <Button  className="mt-4" onClick={() => { setIsOpen(false); window.location.href = RAGFLOW_URL;}}>
   Get Started
</Button>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}