import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { 
  Globe, 
  Smartphone, 
  MessageCircle, 
  Bot,
  Laptop,
  Gamepad2,
  Mail,
  Phone,
  Brain
} from "lucide-react";

export function Platforms() {
  const platforms = [
    {
      category: "Web & Mobile",
      icon: <Globe className="h-6 w-6" />,
      items: ["Websites", "Web Apps", "Mobile Apps", "PWAs", "React Native", "Flutter"]
    },
    {
      category: "Messaging Apps",
      icon: <MessageCircle className="h-6 w-6" />,
      items: ["WhatsApp", "Telegram", "Facebook Messenger", "Instagram DM", "WeChat", "LINE"]
    },
    {
      category: "Business Tools",
      icon: <Laptop className="h-6 w-6" />,
      items: ["Slack", "Microsoft Teams", "Discord", "Notion", "Intercom", "Zendesk"]
    },
    {
      category: "Voice & Others",
      icon: <Phone className="h-6 w-6" />,
      items: ["Voice Assistants", "SMS", "Email", "API Endpoints", "Webhooks", "Custom Bots"]
    }
  ];

  const aiProviders = [
    { name: "OpenAI", description: "GPT models & DALL-E", badge: "Most Popular" },
    { name: "Google", description: "Gemini & PaLM models", badge: "Multimodal" },
    { name: "Anthropic", description: "Claude family", badge: "Reasoning" },
    { name: "xAI", description: "Grok models", badge: "Real-time" },
    { name: "Meta", description: "Llama models", badge: "Open Source" },
    { name: "Mistral AI", description: "Mistral models", badge: "Efficient" },
    { name: "Cohere", description: "Command models", badge: "Enterprise" },
    { name: "Perplexity", description: "Search-enhanced AI", badge: "Research" }
  ];

  return (
    <section className="py-20 px-4">
      <div className="container mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Deploy Anywhere,
            <span className="block text-primary">Choose Any AI Provider</span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            Build once and deploy across all major platforms. Mix and match AI providers 
            to create the perfect conversational experience for your users.
          </p>
        </div>

        {/* Deployment Platforms */}
        <div className="mb-16">
          <h3 className="text-2xl font-bold text-center mb-8">Deployment Platforms</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {platforms.map((platform, index) => (
              <Card key={index} className="text-center">
                <CardHeader>
                  <div className="flex justify-center mb-2 text-primary">
                    {platform.icon}
                  </div>
                  <CardTitle className="text-lg">{platform.category}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {platform.items.map((item, itemIndex) => (
                      <div key={itemIndex} className="text-sm text-muted-foreground">
                        {item}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* AI Providers */}
        <div>
          <h3 className="text-2xl font-bold text-center mb-8">Supported AI Providers</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {aiProviders.map((provider, index) => (
              <Card key={index} className="relative hover:shadow-md transition-shadow">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between mb-2">
                    <Brain className="h-5 w-5 text-primary" />
                    {provider.badge && (
                      <Badge variant="secondary" className="text-xs">
                        {provider.badge}
                      </Badge>
                    )}
                  </div>
                  <h4 className="font-bold mb-1">{provider.name}</h4>
                  <p className="text-sm text-muted-foreground">{provider.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="text-center mt-8">
            <p className="text-muted-foreground">
              And many more... We're constantly adding new AI providers as they become available.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}