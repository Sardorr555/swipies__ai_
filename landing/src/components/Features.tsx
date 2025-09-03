import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { 
  MessageSquare, 
  Brain, 
  Zap, 
  Shield, 
  BarChart3, 
  Puzzle,
  Globe,
  Bot,
  Database,
  Smartphone,
  Code,
  Settings
} from "lucide-react";

export function Features() {
  const features = [
    {
      icon: <Brain className="h-8 w-8 text-primary" />,
      title: "Multiple AI Providers",
      description: "Choose from OpenAI, Google, Anthropic, xAI, Meta, Mistral, and other leading AI providers. Switch between providers instantly.",
      badge: "AI-Powered"
    },
    {
      icon: <Smartphone className="h-8 w-8 text-primary" />,
      title: "Multi-Platform Deployment",
      description: "Deploy to websites, mobile apps, WhatsApp, Telegram, Discord, Slack, Facebook Messenger, Instagram, and more.",
      badge: "Everywhere"
    },
    {
      icon: <Code className="h-8 w-8 text-primary" />,
      title: "Easy Integration",
      description: "Simple SDK, REST APIs, and webhooks. Embed chatbots in any app or website with just a few lines of code.",
      badge: "Developer-Friendly"
    },
    {
      icon: <Zap className="h-8 w-8 text-primary" />,
      title: "No-Code Builder",
      description: "Visual flow builder with drag-and-drop interface. Create complex workflows without programming knowledge.",
      badge: "No-Code"
    },
    {
      icon: <MessageSquare className="h-8 w-8 text-primary" />,
      title: "Omnichannel Experience",
      description: "Unified conversations across all platforms. Users can start on web and continue on WhatsApp seamlessly.",
      badge: "Unified"
    },
    {
      icon: <Settings className="h-8 w-8 text-primary" />,
      title: "Custom Training",
      description: "Train your bots with your own data, documents, and knowledge base. Create domain-specific AI assistants.",
      badge: "Customizable"
    },
    {
      icon: <Shield className="h-8 w-8 text-primary" />,
      title: "Enterprise Security",
      description: "SOC 2 compliant with end-to-end encryption, SSO, role-based access control, and data residency options.",
      badge: "Secure"
    },
    {
      icon: <BarChart3 className="h-8 w-8 text-primary" />,
      title: "Analytics & Insights",
      description: "Real-time dashboards, conversation analytics, user engagement metrics, and AI performance tracking.",
      badge: "Analytics"
    },
    {
      icon: <Puzzle className="h-8 w-8 text-primary" />,
      title: "1000+ Integrations",
      description: "Connect with CRM, helpdesk, e-commerce, databases, and popular business tools through native integrations.",
      badge: "Connected"
    },
    {
      icon: <Globe className="h-8 w-8 text-primary" />,
      title: "Multi-Language Support",
      description: "Support for 100+ languages with automatic translation, localization, and region-specific AI models.",
      badge: "Global"
    },
    {
      icon: <Bot className="h-8 w-8 text-primary" />,
      title: "Human Handoff",
      description: "Seamless escalation to human agents across all platforms with complete conversation context preservation.",
      badge: "Hybrid"
    },
    {
      icon: <Database className="h-8 w-8 text-primary" />,
      title: "Smart Knowledge Base",
      description: "Upload documents, URLs, databases, and files. AI automatically extracts and uses relevant information.",
      badge: "Intelligent"
    }
  ];

  return (
    <section id="features" className="py-20 px-4 bg-muted/20">
      <div className="container mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Everything You Need to Build
            <span className="block text-primary">Powerful AI Agents</span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            From simple chatbots to complex AI workflows across every platform. Deploy once, 
            engage everywhere with the power of multiple AI providers at your fingertips.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <Card key={index} className="relative group hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-center justify-between mb-2">
                  {feature.icon}
                  <Badge variant="secondary">{feature.badge}</Badge>
                </div>
                <CardTitle className="text-xl">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-base">
                  {feature.description}
                </CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}