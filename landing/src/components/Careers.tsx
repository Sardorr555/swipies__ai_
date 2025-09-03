import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { 
  MapPin, 
  Clock, 
  Users, 
  Briefcase,
  Heart,
  Coffee,
  Gamepad2,
  GraduationCap,
  DollarSign,
  Calendar,
  ArrowRight,
  Building,
  Zap
} from "lucide-react";

export function Careers() {
  const jobListings = [
    {
      title: "Senior AI Engineer",
      department: "Engineering",
      location: "San Francisco, CA",
      type: "Full-time",
      experience: "5+ years",
      description: "Join our core AI team to develop cutting-edge conversational AI systems that power millions of interactions daily.",
      requirements: ["Python, TensorFlow/PyTorch", "Large Language Models", "Distributed Systems", "API Design"],
      posted: "2 days ago"
    },
    {
      title: "Product Manager - AI Platform",
      department: "Product",
      location: "Remote",
      type: "Full-time",
      experience: "3+ years",
      description: "Lead product strategy for our AI platform, working closely with engineering and design teams to deliver exceptional user experiences.",
      requirements: ["Product Management", "AI/ML Knowledge", "User Research", "Agile Methodologies"],
      posted: "1 week ago"
    },
    {
      title: "DevOps Engineer",
      department: "Engineering",
      location: "Seattle, WA",
      type: "Full-time",
      experience: "4+ years",
      description: "Scale our infrastructure to handle millions of AI conversations while maintaining high availability and performance.",
      requirements: ["Kubernetes", "AWS/GCP", "CI/CD", "Monitoring & Alerting"],
      posted: "3 days ago"
    },
    {
      title: "UX Designer",
      department: "Design",
      location: "New York, NY",
      type: "Full-time",
      experience: "3+ years",
      description: "Design intuitive interfaces for our conversational AI platform, making complex AI capabilities accessible to everyone.",
      requirements: ["UI/UX Design", "Figma/Sketch", "User Research", "Design Systems"],
      posted: "5 days ago"
    },
    {
      title: "Machine Learning Researcher",
      department: "Research",
      location: "Palo Alto, CA",
      type: "Full-time",
      experience: "PhD preferred",
      description: "Conduct cutting-edge research in conversational AI, multimodal learning, and efficient model architectures.",
      requirements: ["PhD in ML/AI", "Published Research", "Python/PyTorch", "NLP/Computer Vision"],
      posted: "1 week ago"
    },
    {
      title: "Sales Engineer",
      department: "Sales",
      location: "Austin, TX",
      type: "Full-time",
      experience: "2+ years",
      description: "Help enterprise customers integrate our AI platform into their workflows, providing technical expertise during the sales process.",
      requirements: ["Technical Sales", "API Integration", "Customer Success", "Communication Skills"],
      posted: "4 days ago"
    }
  ];

  const benefits = [
    {
      icon: <Heart className="h-6 w-6" />,
      title: "Health & Wellness",
      description: "Comprehensive health, dental, and vision insurance. Mental health support and wellness programs."
    },
    {
      icon: <DollarSign className="h-6 w-6" />,
      title: "Competitive Compensation",
      description: "Market-leading salaries, equity packages, and performance bonuses. Annual compensation reviews."
    },
    {
      icon: <Calendar className="h-6 w-6" />,
      title: "Flexible Time Off",
      description: "Unlimited PTO policy, parental leave, and sabbatical opportunities for long-term employees."
    },
    {
      icon: <GraduationCap className="h-6 w-6" />,
      title: "Learning & Growth",
      description: "Education budget, conference attendance, and access to online learning platforms."
    },
    {
      icon: <Coffee className="h-6 w-6" />,
      title: "Great Perks",
      description: "Free meals, top-tier equipment, commuter benefits, and regular team events."
    },
    {
      icon: <Building className="h-6 w-6" />,
      title: "Remote-First",
      description: "Work from anywhere with occasional in-person team gatherings and beautiful offices."
    }
  ];

  const stats = [
    { icon: <Users className="h-6 w-6" />, label: "Team Size", value: "50+" },
    { icon: <Briefcase className="h-6 w-6" />, label: "Open Positions", value: "15+" },
    { icon: <Gamepad2 className="h-6 w-6" />, label: "Average Tenure", value: "3.5 years" },
    { icon: <Zap className="h-6 w-6" />, label: "Growth Rate", value: "300%" }
  ];

  return (
    <div className="min-h-screen text-foreground">
      {/* Hero Section */}
      <section className="pt-24 pb-12 px-4">
        <div className="container mx-auto text-center">
          <Badge variant="secondary" className="mb-4">
            <Briefcase className="w-3 h-3 mr-1" />
            We're Hiring
          </Badge>
          
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold mb-6 max-w-4xl mx-auto">
            Build the Future of
            <span className="block text-primary">Conversational AI</span>
          </h1>
          
          <p className="text-xl text-muted-foreground mb-12 max-w-3xl mx-auto">
            Join a passionate team of innovators, researchers, and builders creating the next generation 
            of AI-powered conversation platforms. Help us make AI accessible to everyone.
          </p>

          {/* Stats */}
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
      </section>

      {/* Benefits Section */}
      <section className="py-20 px-4 bg-muted/20">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Why Work With Us
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              We believe in taking care of our team so they can do their best work and grow their careers.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {benefits.map((benefit, index) => (
              <Card key={index} className="text-center hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex justify-center mb-4 text-primary">
                    {benefit.icon}
                  </div>
                  <CardTitle className="text-xl">{benefit.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-base">
                    {benefit.description}
                  </CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Job Listings */}
      <section className="py-20 px-4">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Open Positions
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Ready to make an impact? Check out our current openings and find your next adventure.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {jobListings.map((job, index) => (
              <Card key={index} className="group hover:shadow-lg transition-all duration-300">
                <CardHeader>
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <CardTitle className="text-xl mb-2">{job.title}</CardTitle>
                      <div className="flex flex-wrap gap-2 mb-3">
                        <Badge variant="secondary">{job.department}</Badge>
                        <Badge variant="outline">{job.type}</Badge>
                        <Badge variant="outline">{job.experience}</Badge>
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {job.posted}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
                    <div className="flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      <span>{job.location}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      <span>{job.type}</span>
                    </div>
                  </div>
                </CardHeader>
                
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {job.description}
                  </p>
                  
                  <div>
                    <h4 className="text-sm font-medium mb-2">Key Requirements</h4>
                    <div className="flex flex-wrap gap-1">
                      {job.requirements.map((req, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                          {req}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <Button className="w-full group-hover:bg-primary/90 transition-colors">
                    Apply Now
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="py-20 px-4 bg-muted/20">
        <div className="container mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Don't See the Right Role?
          </h2>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            We're always looking for exceptional talent. Send us your resume and let us know how you'd like to contribute.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" className="text-lg px-8 py-6">
              Send General Application
            </Button>
            <Button variant="outline" size="lg" className="text-lg px-8 py-6">
              Join Our Talent Pool
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}