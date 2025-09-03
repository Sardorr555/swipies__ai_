/*import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { Button } from "./ui/button";
import { 
  Linkedin, 
  Twitter, 
  Github, 
  Mail,
  MapPin,
  Calendar,
  Award,
  Users,
  Code,
  Brain
} from "lucide-react";
import { ImageWithFallback } from "./figma/ImageWithFallback";

export function Team() {
  const teamMembers = [
    {
      name: "Albakiev Sardorbek",
      role: "CEO & Founder",
      image: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&h=400&fit=crop&crop=face",
      bio: "Visionary leader with 10+ years in AI and machine learning. Previously led AI initiatives at major tech companies.",
      location: "San Francisco, CA",
      joinDate: "2023",
      specialties: ["AI Strategy", "Product Vision", "Team Leadership"],
      social: {
        linkedin: "#",
        twitter: "#",
        email: "sardorbek@swipiesai.com"
      },
      achievements: ["Forbes 30 Under 30", "AI Innovation Award 2023"]
    },
    {
      name: "Sarah Chen",
      role: "CTO & Co-Founder",
      image: "https://images.unsplash.com/photo-1494790108755-2616b612b647?w=400&h=400&fit=crop&crop=face",
      bio: "Former Google AI engineer with expertise in large language models and conversational AI systems.",
      location: "Seattle, WA",
      joinDate: "2023",
      specialties: ["Machine Learning", "System Architecture", "AI Research"],
      social: {
        linkedin: "#",
        github: "#",
        email: "sarah@swipiesai.com"
      },
      achievements: ["Google AI Research Award", "MIT Tech Review Innovator"]
    },
    {
      name: "Marcus Johnson",
      role: "VP of Engineering",
      image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop&crop=face",
      bio: "Full-stack engineering leader with experience scaling platforms to millions of users at Slack and Discord.",
      location: "Austin, TX",
      joinDate: "2023",
      specialties: ["Platform Engineering", "DevOps", "Team Management"],
      social: {
        linkedin: "#",
        github: "#",
        email: "marcus@swipiesai.com"
      },
      achievements: ["Engineering Excellence Award", "Open Source Contributor"]
    },
    {
      name: "Dr. Priya Patel",
      role: "Head of AI Research",
      image: "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=400&h=400&fit=crop&crop=face",
      bio: "PhD in Natural Language Processing from Stanford. Leading research in multimodal AI and conversational agents.",
      location: "Palo Alto, CA",
      joinDate: "2023",
      specialties: ["NLP Research", "Multimodal AI", "Academic Partnerships"],
      social: {
        linkedin: "#",
        twitter: "#",
        email: "priya@swipiesai.com"
      },
      achievements: ["AAAI Fellow", "Best Paper Award ACL 2023"]
    },
    {
      name: "Alex Rivera",
      role: "VP of Product",
      image: "https://images.unsplash.com/photo-1519244703995-f4e0f30006d5?w=400&h=400&fit=crop&crop=face",
      bio: "Product strategist who previously built conversational AI products at Microsoft and Salesforce.",
      location: "New York, NY",
      joinDate: "2023",
      specialties: ["Product Strategy", "User Experience", "Go-to-Market"],
      social: {
        linkedin: "#",
        twitter: "#",
        email: "alex@swipiesai.com"
      },
      achievements: ["Product Leader of the Year", "Customer Success Champion"]
    },
    {
      name: "Emma Thompson",
      role: "Head of Design",
      image: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=400&fit=crop&crop=face",
      bio: "Design systems expert who crafted user experiences for millions at Airbnb and Stripe.",
      location: "Los Angeles, CA",
      joinDate: "2023",
      specialties: ["UX Design", "Design Systems", "User Research"],
      social: {
        linkedin: "#",
        twitter: "#",
        email: "emma@swipiesai.com"
      },
      achievements: ["Design Team of the Year", "UX Excellence Award"]
    }
  ];

  const stats = [
    { icon: <Users className="h-6 w-6" />, label: "Team Members", value: "50+" },
    { icon: <Code className="h-6 w-6" />, label: "Engineers", value: "30+" },
    { icon: <Brain className="h-6 w-6" />, label: "AI Researchers", value: "12+" },
    { icon: <Award className="h-6 w-6" />, label: "Industry Awards", value: "15+" }
  ];

  return (
    <div className="min-h-screen text-foreground">*/
      {/* Hero Section */}/*
      <section className="pt-24 pb-12 px-4">
        <div className="container mx-auto text-center">
          <Badge variant="secondary" className="mb-4">
            <Users className="w-3 h-3 mr-1" />
            Meet Our Team
          </Badge>
          
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold mb-6 max-w-4xl mx-auto">
            The Minds Behind
            <span className="block text-primary">Swipies AI</span>
          </h1>
          
          <p className="text-xl text-muted-foreground mb-12 max-w-3xl mx-auto">
            We're a diverse team of AI researchers, engineers, and product experts passionate about 
            building the future of conversational AI. Meet the people making it happen.
          </p>

          {/* Stats */    /*
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-2xl mx-auto">
            {stats.map((stat, index) => (
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
      </section>*/

      {/* Team Grid */}/*
      <section className="py-20 px-4 bg-muted/20">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Leadership Team
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Experienced leaders from top tech companies, united by a shared vision 
              of making AI accessible to everyone.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {teamMembers.map((member, index) => (
              <Card key={index} className="group hover:shadow-lg transition-all duration-300">
                <CardHeader className="text-center">
                  <div className="relative mx-auto mb-4">
                    <Avatar className="w-24 h-24 mx-auto border-4 border-primary/10">
                      <AvatarImage src={member.image} alt={member.name} />
                      <AvatarFallback>{member.name.split(' ').map(n => n[0]).join('')}</AvatarFallback>
                    </Avatar>
                  </div>
                  <CardTitle className="text-xl">{member.name}</CardTitle>
                  <CardDescription className="text-primary font-medium">
                    {member.role}
                  </CardDescription>
                  <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                    <MapPin className="h-3 w-3" />
                    <span>{member.location}</span>
                    <span>•</span>
                    <Calendar className="h-3 w-3" />
                    <span>Since {member.joinDate}</span>
                  </div>
                </CardHeader>
                
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {member.bio}
                  </p>*/
                  
                  {/* Specialties */}/*
                  <div>
                    <h4 className="text-sm font-medium mb-2">Specialties</h4>
                    <div className="flex flex-wrap gap-1">
                      {member.specialties.map((specialty, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                          {specialty}
                        </Badge>
                      ))}
                    </div>
                  </div>
*/
                  {/* Achievements */}
                  /*
                  <div>
                    <h4 className="text-sm font-medium mb-2">Achievements</h4>
                    <div className="space-y-1">
                      {member.achievements.map((achievement, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Award className="h-3 w-3 text-primary" />
                          <span>{achievement}</span>
                        </div>
                      ))}
                    </div>
                  </div>
*/
                  {/* Social Links */}/*
                  <div className="flex justify-center gap-2 pt-2">
                    {member.social.linkedin && (
                      <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
                        <Linkedin className="h-4 w-4" />
                      </Button>
                    )}
                    {member.social.twitter && (
                      <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
                        <Twitter className="h-4 w-4" />
                      </Button>
                    )}
                    {member.social.github && (
                      <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
                        <Github className="h-4 w-4" />
                      </Button>
                    )}
                    {member.social.email && (
                      <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
                        <Mail className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>*/

      {/* Join Us Section */}
      /*
      <section className="py-20 px-4">
        <div className="container mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Join Our Mission
          </h2>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            We're always looking for talented individuals who share our passion for AI innovation. 
            Help us build the future of conversational AI.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" className="text-lg px-8 py-6">
              View Open Positions
            </Button>
            <Button variant="outline" size="lg" className="text-lg px-8 py-6">
              <Mail className="mr-2 h-5 w-5" />
              Contact HR
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}*/