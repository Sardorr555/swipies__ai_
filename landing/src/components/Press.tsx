import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { 
  Calendar, 
  ExternalLink, 
  Download,
  FileText,
  Newspaper,
  Award,
  TrendingUp,
  Users,
  Building,
  Globe
} from "lucide-react";
import { ImageWithFallback } from "./figma/ImageWithFallback";

export function Press() {
  const pressReleases = [
    {
      title: "Swipies AI Raises $50M Series B to Democratize Conversational AI",
      date: "January 15, 2025",
      excerpt: "Funding round led by Andreessen Horowitz will accelerate platform development and global expansion as demand for AI chatbots surges across industries.",
      category: "Funding",
      featured: true
    },
    {
      title: "Swipies AI Launches Multi-Modal AI Support for Voice and Video Interactions",
      date: "December 8, 2024",
      excerpt: "New capabilities enable businesses to create AI agents that can understand and respond through voice, video, and text across all messaging platforms.",
      category: "Product"
    },
    {
      title: "Swipies AI Partners with Microsoft to Integrate Azure OpenAI Services",
      date: "November 22, 2024",
      excerpt: "Strategic partnership brings enterprise-grade AI capabilities to Microsoft's ecosystem, enabling seamless deployment of conversational AI solutions.",
      category: "Partnership"
    },
    {
      title: "CEO Albakiev Sardorbek Named to Forbes 30 Under 30 List",
      date: "October 30, 2024",
      excerpt: "Recognition highlights leadership in democratizing AI technology and building platforms that make advanced AI accessible to businesses of all sizes.",
      category: "Award"
    }
  ];

  const mediaCoverage = [
    {
      outlet: "TechCrunch",
      title: "How Swipies AI is Making Chatbot Development Accessible to Everyone",
      date: "January 10, 2025",
      type: "Feature Article",
      logo: "https://images.unsplash.com/photo-1611605698335-8b1569810432?w=100&h=60&fit=crop"
    },
    {
      outlet: "VentureBeat",
      title: "The Rise of No-Code AI: Swipies AI's Platform Approach",
      date: "December 15, 2024",
      type: "Analysis",
      logo: "https://images.unsplash.com/photo-1586953208448-b95a79798f07?w=100&h=60&fit=crop"
    },
    {
      outlet: "The Information",
      title: "Inside Swipies AI's Strategy to Compete with ChatGPT Enterprise",
      date: "November 28, 2024",
      type: "Exclusive",
      logo: "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=100&h=60&fit=crop"
    },
    {
      outlet: "Forbes",
      title: "Young CEO Building the Future of Conversational AI",
      date: "October 25, 2024",
      type: "Profile",
      logo: "https://images.unsplash.com/photo-1586953208448-b95a79798f07?w=100&h=60&fit=crop"
    }
  ];

  const awards = [
    {
      title: "Best AI Platform 2024",
      organization: "AI Excellence Awards",
      date: "December 2024",
      icon: <Award className="h-6 w-6" />
    },
    {
      title: "Innovation in Conversational AI",
      organization: "TechCrunch Disrupt",
      date: "September 2024",
      icon: <TrendingUp className="h-6 w-6" />
    },
    {
      title: "Startup of the Year",
      organization: "Silicon Valley Business Journal",
      date: "August 2024",
      icon: <Building className="h-6 w-6" />
    }
  ];

  const companyStats = [
    { icon: <Users className="h-6 w-6" />, label: "Active Users", value: "50,000+" },
    { icon: <Globe className="h-6 w-6" />, label: "Countries", value: "25+" },
    { icon: <FileText className="h-6 w-6" />, label: "API Calls/Month", value: "100M+" },
    { icon: <Building className="h-6 w-6" />, label: "Enterprise Clients", value: "500+" }
  ];

  return (
    <div className="min-h-screen text-foreground">
      {/* Hero Section */}
      <section className="pt-24 pb-12 px-4">
        <div className="container mx-auto text-center">
          <Badge variant="secondary" className="mb-4">
            <Newspaper className="w-3 h-3 mr-1" />
            Press & Media
          </Badge>
          
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold mb-6 max-w-4xl mx-auto">
            Latest News &
            <span className="block text-primary">Media Coverage</span>
          </h1>
          
          <p className="text-xl text-muted-foreground mb-12 max-w-3xl mx-auto">
            Stay updated with the latest news, press releases, and media coverage about 
            Swipies AI and our mission to democratize conversational AI technology.
          </p>

          {/* Company Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-2xl mx-auto">
            {companyStats.map((stat, index) => (
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

      {/* Press Releases */}
      <section className="py-20 px-4 bg-muted/20">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Press Releases
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Official company announcements and news updates.
            </p>
          </div>

          <div className="space-y-6">
            {pressReleases.map((release, index) => (
              <Card key={index} className={`group hover:shadow-lg transition-all duration-300 ${release.featured ? 'border-primary/50' : ''}`}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant={release.featured ? "default" : "secondary"}>
                          {release.category}
                        </Badge>
                        {release.featured && (
                          <Badge variant="outline">Featured</Badge>
                        )}
                      </div>
                      <CardTitle className="text-xl mb-2 group-hover:text-primary transition-colors">
                        {release.title}
                      </CardTitle>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
                        <Calendar className="h-3 w-3" />
                        <span>{release.date}</span>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                
                <CardContent>
                  <p className="text-muted-foreground mb-4 leading-relaxed">
                    {release.excerpt}
                  </p>
                  <div className="flex gap-2">
                    <Button size="sm">
                      Read Full Release
                      <ExternalLink className="ml-2 h-3 w-3" />
                    </Button>
                    <Button size="sm" variant="outline">
                      <Download className="mr-2 h-3 w-3" />
                      Download PDF
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Media Coverage */}
      <section className="py-20 px-4">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Media Coverage
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              What leading publications are saying about Swipies AI.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {mediaCoverage.map((article, index) => (
              <Card key={index} className="group hover:shadow-lg transition-all duration-300">
                <CardHeader>
                  <div className="flex items-center gap-4 mb-4">
                    <ImageWithFallback 
                      src={article.logo} 
                      alt={article.outlet}
                      className="w-16 h-10 object-cover rounded border"
                    />
                    <div>
                      <h3 className="font-bold text-primary">{article.outlet}</h3>
                      <Badge variant="outline" className="text-xs">
                        {article.type}
                      </Badge>
                    </div>
                  </div>
                  <CardTitle className="text-lg group-hover:text-primary transition-colors">
                    {article.title}
                  </CardTitle>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Calendar className="h-3 w-3" />
                    <span>{article.date}</span>
                  </div>
                </CardHeader>
                
                <CardContent>
                  <Button size="sm" className="w-full">
                    Read Article
                    <ExternalLink className="ml-2 h-3 w-3" />
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Awards & Recognition */}
      <section className="py-20 px-4 bg-muted/20">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Awards & Recognition
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Industry recognition for our innovation and leadership in AI.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {awards.map((award, index) => (
              <Card key={index} className="text-center hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex justify-center mb-4 text-primary">
                    {award.icon}
                  </div>
                  <CardTitle className="text-lg">{award.title}</CardTitle>
                  <CardDescription>{award.organization}</CardDescription>
                  <div className="text-sm text-muted-foreground mt-2">
                    {award.date}
                  </div>
                </CardHeader>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Media Kit */}
      <section className="py-20 px-4">
        <div className="container mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Media Kit
          </h2>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Looking to write about Swipies AI? Download our media kit with logos, photos, and company information.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" className="text-lg px-8 py-6">
              <Download className="mr-2 h-5 w-5" />
              Download Media Kit
            </Button>
            <Button variant="outline" size="lg" className="text-lg px-8 py-6">
              Contact Press Team
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}