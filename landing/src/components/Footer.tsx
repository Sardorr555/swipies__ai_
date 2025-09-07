import { Separator } from "./ui/separator";
import { Twitter, Github, Linkedin, Mail } from "lucide-react";
import { LINKS } from "@/config";

export function Footer() {
  return (
    <footer className="bg-muted/20 pt-16 pb-8 px-4">
      <div className="container mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Company Info */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <span className="text-primary-foreground font-bold">S</span>
              </div>
              <span className="text-xl font-bold">Swipies AI</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Building the future of conversational AI. 
              Empowering businesses with intelligent chatbots.
            </p>
            <div className="flex space-x-4">
              <a href={LINKS.social.twitter} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">
                <Twitter className="h-5 w-5" />
              </a>
              <a href={LINKS.social.github} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">
                <Github className="h-5 w-5" />
              </a>
              <a href={LINKS.social.linkedin} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">
                <Linkedin className="h-5 w-5" />
              </a>
              <a href={`mailto:${LINKS.social.email}`} className="text-muted-foreground hover:text-primary">
                <Mail className="h-5 w-5" />
              </a>
            </div>
          </div>

          {/* Product */}
          <div className="space-y-4">
            <h4 className="font-bold">Product</h4>
            <ul className="space-y-2 text-sm">
              <li><a href={LINKS.product.features} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">Features</a></li>
              <li><a href={LINKS.product.pricing} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">Pricing</a></li>
              <li><a href={LINKS.product.integrations} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">Integrations</a></li>
              <li><a href={LINKS.product.api} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">API</a></li>
              <li><a href={LINKS.product.changelog} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">Changelog</a></li>
            </ul>
          </div>

          {/* Support */}
          <div className="space-y-4">
            <h4 className="font-bold">Support</h4>
            <ul className="space-y-2 text-sm">
              <li><a href={LINKS.support.helpCenter} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">Help Center</a></li>
              <li><a href={LINKS.support.documentation} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">Documentation</a></li>
              <li><a href={LINKS.support.tutorials} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">Tutorials</a></li>
              <li><a href={LINKS.support.community} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">Community</a></li>
              <li><a href={LINKS.support.contact} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">Contact</a></li>
            </ul>
          </div>

          {/* Company */}
          <div className="space-y-4">
            <h4 className="font-bold">Company</h4>
            <ul className="space-y-2 text-sm">
              <li><a href={LINKS.company.about} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">About</a></li>
              <li><a href={LINKS.company.blog} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">Blog</a></li>
              <li><a href={LINKS.company.careers} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">Careers</a></li>
              <li><a href={LINKS.company.press} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">Press</a></li>
              <li><a href={LINKS.company.partners} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">Partners</a></li>
            </ul>
          </div>
        </div>

        <Separator className="my-8" />

        <div className="flex flex-col md:flex-row justify-between items-center text-sm text-muted-foreground">
          <p>&copy; 2024 Swipies AI. All rights reserved.</p>
          <div className="flex space-x-6 mt-4 md:mt-0">
            <a href={LINKS.policies.privacy} target="_blank" rel="noopener noreferrer" className="hover:text-primary">Privacy Policy</a>
            <a href={LINKS.policies.terms} target="_blank" rel="noopener noreferrer" className="hover:text-primary">Terms of Service</a>
            <a href={LINKS.policies.cookies} target="_blank" rel="noopener noreferrer" className="hover:text-primary">Cookie Policy</a>
          </div>
        </div>
      </div>
    </footer>
  );
}