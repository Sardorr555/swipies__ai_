import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { 
  Handshake, 
  Building, 
  Zap,
  Globe,
  Users,
  Award,
  ArrowRight,
  CheckCircle,
  Star,
  Target,
  Rocket,
  Shield
} from "lucide-react";
import { ImageWithFallback } from "./figma/ImageWithFallback";

export function Partners() {
  const technologyPartners = [
    {
      name: "Microsoft Azure",
      logo: "https://images.unsplash.com/photo-1633409361618-c73427e4e206?w=120&h=80&fit=crop",
      category: "Cloud Infrastructure",
      description: "Strategic partnership providing enterprise-grade cloud infrastructure and AI services through Azure OpenAI.",
      badge: "Strategic Partner"
    },
    {
      name: "OpenAI",
      logo: "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=120&h=80&fit=crop",
      category: "AI Models",
      description: "Official partner providing access to latest GPT models and cutting-edge language capabilities.",
      badge: "AI Partner"
    },
    {
      name: "Google Cloud",
      logo: "https://images.unsplash.com/photo-1573804633927-bfcbcd909acd?w=120&h=80&fit=crop",
      category: "Cloud & AI",
      description: "Integration with Google Cloud AI platform and Vertex AI for scalable machine learning solutions.",
      badge: "Technology Partner"
    },
    {
      name: "Anthropic",
      logo: "https://images.unsplash.com/photo-1611605698335-8b1569810432?w=120&h=80&fit=crop",
      category: "AI Safety",
      description: "Partnership bringing Claude's advanced reasoning capabilities to our conversational AI platform.",
      badge: "AI Partner"
    },
    {
      name: "Salesforce",
      logo: "https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=120&h=80&fit=crop",
      category: "CRM Integration",
      description: "Deep integration with Salesforce CRM enabling seamless customer data and workflow automation.",
      badge: "Integration Partner"
    },
    {
      name: "Slack",
      logo: "https://images.unsplash.com/photo-1611605698335-8b1569810432?w=120&h=80&fit=crop",
      category: "Workplace",
      description: "Native Slack integration for internal AI assistants and customer support automation.",
      badge: "Platform Partner"
    }
  ];

  const integrationPartners = [
    {
      name: "Zapier",
      logo: "https://images.unsplash.com/photo-1586953208448-b95a79798f07?w=80&h=80&fit=crop",
      category: "Automation"
    },
    {
      name: "HubSpot",
      logo: "https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=80&h=80&fit=crop",
      category: "Marketing"
    },
    {
      name: "Shopify",
      logo: "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=80&h=80&fit=crop",
      category: "E-commerce"
    },
    {
      name: "Stripe",
      logo: "https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=80&h=80&fit=crop",
      category: "Payments"
    },
    {
      name: "Twilio",
      logo: "https://images.unsplash.com/photo-1611605698335-8b1569810432?w=80&h=80&fit=crop",
      category: "Communications"
    },
    {
      name: "Zendesk",
      logo: "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=80&h=80&fit=crop",
      category: "Support"
    }
  ];

  const partnershipTypes = [
    {
      icon: <Building className="h-8 w-8" />,
      title: "Technology Partners",
      description: "Integrate your platform with Swipies AI to provide enhanced AI capabilities to your customers.",
      benefits: ["Technical integration support", "Joint go-to-market opportunities", "Co-marketing initiatives", "Dedicated partner success team"],
      cta: "Apply as Technology Partner"
    },
    {
      icon: <Users className="h-8 w-8" />,
      title: "Solution Partners",
      description: "Build and deliver AI solutions using our platform for your clients across various industries.",
      benefits: ["Training and certification", "Sales enablement resources", "Lead sharing programs", "Priority technical support"],
      cta: "Become Solution Partner"
    },
    {
      icon: <Rocket className="h-8 w-8" />,
      title: "Startup Partners",
      description: "Special partnership program for startups looking to integrate conversational AI into their products.",
      benefits: ["Reduced pricing tiers", "Technical mentorship", "Investor network access", "Product development support"],
      cta: "Join Startup Program"
    }
  ];

  const partnerStats = [
    { icon: <Handshake className="h-6 w-6" />, label: "Active Partners", value: "150+" },
    { icon: <Globe className="h-6 w-6" />, label: "Integration Partners", value: "50+" },
    { icon: <Award className="h-6 w-6" />, label: "Certified Partners", value: "75+" },
    { icon: <Target className="h-6 w-6" />, label: "Joint Customers", value: "1,000+" }
  ];

  return (
    <div className="min-h-screen text-foreground">
      {/* Hero Section */}
      <section className="pt-24 pb-12 px-4">
        <div className="container mx-auto text-center">
          <Badge variant="secondary" className="mb-4">
            <Handshake className="w-3 h-3 mr-1" />
            Partner Ecosystem
          </Badge>
          
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold mb-6 max-w-4xl mx-auto">
            Build Together,
            <span className="block text-primary">Grow Together</span>
          </h1>
          
          <p className="text-xl text-muted-foreground mb-12 max-w-3xl mx-auto">
            Join our growing ecosystem of technology partners, solution providers, and integrations. 
            Together, we're making conversational AI accessible to businesses worldwide.
          </p>

          {/* Partner Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-2xl mx-auto">
            {partnerStats.map((stat, index) => (
              <div key={index} className="text-center">
                <div className="flex justify-center mb-2 text-primary">
                  {stat.icon}
                </div>
                <div className="text-2xl font-bold mb-1">{stat.value}</div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Technology Partners */}
      <section className="py-20 px-4 bg-muted/20">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Technology Partners
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Strategic partnerships with leading technology companies to deliver the best AI experience.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {technologyPartners.map((partner, index) => (
              <Card key={index} className="group hover:shadow-lg transition-all duration-300">
                <CardHeader>
                  <div className="flex items-center justify-between mb-4">
                    <ImageWithFallback 
                      src={partner.logo} 
                      alt={partner.name}
                      className="w-16 h-12 object-cover rounded border"
                    />
                    <Badge variant="secondary">{partner.badge}</Badge>
                  </div>
                  <CardTitle className="text-xl">{partner.name}</CardTitle>
                  <CardDescription className="text-primary font-medium">
                    {partner.category}
                  </CardDescription>
                </CardHeader>
                
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {partner.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Integration Partners */}
      <section className="py-20 px-4">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Integration Partners
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Seamlessly connect with your favorite tools and platforms through our extensive integration network.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
            {integrationPartners.map((partner, index) => (
              <Card key={index} className="group hover:shadow-md transition-all duration-300 text-center">
                <CardContent className="pt-6">
                  <ImageWithFallback 
                    src={partner.logo} 
                    alt={partner.name}
                    className="w-12 h-12 mx-auto mb-3 object-cover rounded"
                  />
                  <h4 className="font-medium text-sm mb-1">{partner.name}</h4>
                  <p className="text-xs text-muted-foreground">{partner.category}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="text-center mt-12">
            <Button size="lg" variant="outline">
              View All Integrations
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      </section>

      {/* Partnership Programs */}
      <section className="py-20 px-4 bg-muted/20">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Partnership Programs
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Choose the partnership model that fits your business goals and start building with us.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {partnershipTypes.map((program, index) => (
              <Card key={index} className="group hover:shadow-lg transition-all duration-300">
                <CardHeader>
                  <div className="flex justify-center mb-4 text-primary">
                    {program.icon}
                  </div>
                  <CardTitle className="text-xl text-center">{program.title}</CardTitle>
                  <CardDescription className="text-center">
                    {program.description}
                  </CardDescription>
                </CardHeader>
                
                <CardContent className="space-y-4">
                  <div>
                    <h4 className="font-medium mb-3">Benefits Include:</h4>
                    <div className="space-y-2">
                      {program.benefits.map((benefit, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-sm">
                          <CheckCircle className="h-4 w-4 text-primary flex-shrink-0" />
                          <span>{benefit}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  <Button className="w-full">
                    {program.cta}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Partner Success Stories */}
      <section className="py-20 px-4">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Partner Success Stories
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              See how our partners are driving growth and innovation with Swipies AI.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <Card className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-center gap-4 mb-4">
                  <ImageWithFallback 
                    src="https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=60&h=60&fit=crop" 
                    alt="TechCorp"
                    className="w-12 h-12 rounded-full"
                  />
                  <div>
                    <h3 className="font-bold">TechCorp Solutions</h3>
                    <p className="text-sm text-muted-foreground">Solution Partner</p>
                  </div>
                  <div className="ml-auto flex">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className="h-4 w-4 fill-primary text-primary" />
                    ))}
                  </div>
                </div>
                <CardTitle className="text-lg">
                  "300% Increase in Customer Engagement"
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground mb-4">
                  "Partnering with Swipies AI has transformed how we deliver customer support solutions. Our clients see 3x higher engagement rates and 50% faster resolution times."
                </p>
                <p className="text-sm font-medium">— Sarah Johnson, CEO</p>
              </CardContent>
            </Card>

            <Card className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-center gap-4 mb-4">
                  <ImageWithFallback 
                    src="https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=60&h=60&fit=crop" 
                    alt="RetailBot"
                    className="w-12 h-12 rounded-full"
                  />
                  <div>
                    <h3 className="font-bold">RetailBot Inc</h3>
                    <p className="text-sm text-muted-foreground">Technology Partner</p>
                  </div>
                  <div className="ml-auto flex">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className="h-4 w-4 fill-primary text-primary" />
                    ))}
                  </div>
                </div>
                <CardTitle className="text-lg">
                  "Seamless Integration, Powerful Results"
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground mb-4">
                  "The API integration was incredibly smooth. We built our e-commerce chatbot in just two weeks and now process over 10,000 customer inquiries daily."
                </p>
                <p className="text-sm font-medium">— Mike Chen, CTO</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="py-20 px-4 bg-muted/20">
        <div className="container mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Ready to Partner With Us?
          </h2>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Join our thriving partner ecosystem and unlock new opportunities for growth and innovation.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" className="text-lg px-8 py-6">
              Apply for Partnership
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <Button variant="outline" size="lg" className="text-lg px-8 py-6">
              Partner Portal Login
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}