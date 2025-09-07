import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Play, ArrowRight, Zap, Users, Shield, Smartphone, Globe, MessageCircle } from "lucide-react";
import { DEMO_VIDEO_URL, LINKS } from "@/config";

export function Hero() {
  return (
    <section className="pt-24 pb-12 px-4">
      <div className="container mx-auto text-center">
        <Badge variant="secondary" className="mb-4">
          <Zap className="w-3 h-3 mr-1" />
          New: Multi-AI Provider Support
        </Badge>
        
        <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold mb-6 max-w-4xl mx-auto">
          Deploy AI Chatbots
          <span className="block text-primary">Everywhere</span>
          Your Users Are
        </h1>
        
        <p className="text-xl text-muted-foreground mb-8 max-w-3xl mx-auto">
          Build once, deploy everywhere. Create intelligent chatbots with OpenAI, Google, Anthropic, xAI, and other leading AI providers. 
          Integrate seamlessly into your apps, websites, WhatsApp, Telegram, Discord, and more.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
          <Button asChild size="lg" className="text-lg px-8 py-6">
            <a href={LINKS.getStarted} target="_blank" rel="noopener noreferrer">
              Start Building Free
              <ArrowRight className="ml-2 h-5 w-5" />
            </a>
          </Button>
          <Button asChild variant="outline" size="lg" className="text-lg px-8 py-6">
            <a href={DEMO_VIDEO_URL} target="_blank" rel="noopener noreferrer">
              <Play className="mr-2 h-5 w-5" />
              Watch Demo
            </a>
          </Button>
        </div>
        
        <div className="flex flex-wrap justify-center items-center gap-8 text-sm text-muted-foreground mb-8">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            <span>50+ Active Users</span>
          </div>
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            <span>Enterprise Security</span>
          </div>
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4" />
            <span>100+ AI Providers</span>
          </div>
        </div>

        {/* Platform Icons */}
        <div className="flex flex-wrap justify-center items-center gap-6 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4" />
            <span>Web & Mobile Apps</span>
          </div>
          <div className="flex items-center gap-2">
            <MessageCircle className="h-4 w-4" />
            <span>WhatsApp & Telegram</span>
          </div>
          <div className="flex items-center gap-2">
            <Smartphone className="h-4 w-4" />
            <span>Discord & Slack</span>
          </div>
        </div>
      </div>
    </section>
  );
}