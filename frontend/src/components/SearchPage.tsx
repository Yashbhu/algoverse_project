
import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Search, ArrowLeft, FileText, User } from "lucide-react";
import { useNavigate } from 'react-router-dom';
import { useToast } from "@/hooks/use-toast";

const SearchPage = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [formData, setFormData] = useState({
    name: '',
    city: '',
    extraTerms: ''
  });
  const [isSearching, setIsSearching] = useState(false);
  const [hasResults, setHasResults] = useState(false);
  const [personData, setPersonData] = useState<any>(null);
  const [currentQuote, setCurrentQuote] = useState(0);

  const osintQuotes = [
    "Information is the currency of the digital age.",
    "In data we trust, in ethics we must.",
    "Intelligence gathering with moral boundaries.",
    "Knowledge is power, responsibility is wisdom.",
    "The art of finding needles in digital haystacks.",
    "Privacy and transparency in perfect balance."
  ];

  const handleSearch = async () => {
    setIsSearching(true);
    setHasResults(false);
    
    // Simulate quote rotation during search
    const quoteInterval = setInterval(() => {
      setCurrentQuote((prev) => (prev + 1) % osintQuotes.length);
    }, 2000);

    try {
      // TODO: Replace with your actual backend API call
      // const response = await fetch('/api/search', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(formData)
      // });
      // const data = await response.json();
      
      // Simulate API call for now
      setTimeout(() => {
        clearInterval(quoteInterval);
        setIsSearching(false);
        setHasResults(true);
        
        // Mock data - replace with actual API response
        setPersonData({
          name: formData.name,
          location: formData.city,
          summary: "This is where your backend will provide a comprehensive summary of the person's publicly available information. Connect your backend API to replace this placeholder text.",
          confidence: "85%",
          lastUpdated: new Date().toLocaleDateString()
        });
        
        toast({
          title: "Search Completed",
          description: "Person information has been retrieved successfully."
        });
      }, 6000);
    } catch (error) {
      clearInterval(quoteInterval);
      setIsSearching(false);
      toast({
        title: "Search Failed",
        description: "Unable to retrieve information. Please try again.",
        variant: "destructive"
      });
    }
  };

  const handleGenerateReport = async () => {
    if (!personData) {
      toast({
        title: "No Data Available",
        description: "Please perform a search first to generate a report.",
        variant: "destructive"
      });
      return;
    }

    try {
      // TODO: Replace with your actual report generation API
      // const response = await fetch('/api/generate-report', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(personData)
      // });
      
      toast({
        title: "Report Generated",
        description: "A detailed report has been created and will be available for download shortly."
      });
      
      // Simulate report generation
      console.log('Generating report for:', personData);
      
      // You can add actual report generation logic here
      // For example, creating a PDF or sending to an email
      
    } catch (error) {
      toast({
        title: "Report Generation Failed",
        description: "Unable to generate report. Please try again.",
        variant: "destructive"
      });
    }
  };

  return (
    <div className="min-h-screen bg-black relative overflow-hidden">
      {/* Purple Grid Background */}
      <div className="absolute inset-0 opacity-20">
        <div 
          className="w-full h-full bg-repeat opacity-40"
          style={{
            backgroundImage: `
              linear-gradient(rgba(147, 51, 234, 0.3) 1px, transparent 1px),
              linear-gradient(90deg, rgba(147, 51, 234, 0.3) 1px, transparent 1px)
            `,
            backgroundSize: '40px 40px'
          }}
        />
      </div>

      {/* Animated Background Nodes */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-20 left-20 w-2 h-2 bg-purple-400 rounded-full animate-pulse opacity-60"></div>
        <div className="absolute top-40 right-32 w-1 h-1 bg-purple-300 rounded-full animate-ping opacity-40"></div>
        <div className="absolute bottom-32 left-1/4 w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse opacity-50"></div>
        <div className="absolute top-60 left-1/2 w-1 h-1 bg-purple-400 rounded-full animate-ping opacity-30"></div>
        <div className="absolute bottom-20 right-20 w-2 h-2 bg-purple-300 rounded-full animate-pulse opacity-40"></div>
      </div>

      {/* Back Button */}
      <div className="absolute top-8 left-8 z-10">
        <Button
          onClick={() => navigate('/')}
          className="bg-gray-900/60 backdrop-blur-sm border border-purple-400/30 hover:bg-gray-800/60 text-purple-200"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Home
        </Button>
      </div>

      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="w-full max-w-2xl space-y-8">
          
          {/* Search Form */}
          <Card className="bg-gray-900/60 backdrop-blur-sm border border-purple-400/30 p-8">
            <div className="space-y-6">
              <div className="text-center">
                <h1 className="text-3xl font-bold text-purple-400 glow-text-purple mb-2">OSINT Search</h1>
                <p className="text-purple-200/70">Enter search parameters below</p>
              </div>

              {/* Disclaimer */}
              <div className="bg-red-900/20 border border-red-500/30 p-4 rounded-lg backdrop-blur-sm">
                <p className="text-red-300 text-sm">
                  <strong>Disclaimer:</strong> Do not use this tool for stalking or illegal purposes.
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <Label htmlFor="name" className="text-purple-200">Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    className="bg-gray-800/60 border-purple-400/30 text-purple-100 focus:border-purple-400 backdrop-blur-sm"
                    placeholder="Enter target name"
                  />
                </div>

                <div>
                  <Label htmlFor="city" className="text-purple-200">City</Label>
                  <Input
                    id="city"
                    value={formData.city}
                    onChange={(e) => setFormData({...formData, city: e.target.value})}
                    className="bg-gray-800/60 border-purple-400/30 text-purple-100 focus:border-purple-400 backdrop-blur-sm"
                    placeholder="Enter city"
                  />
                </div>

                <div>
                  <Label htmlFor="extraTerms" className="text-purple-200">Extra Terms</Label>
                  <Input
                    id="extraTerms"
                    value={formData.extraTerms}
                    onChange={(e) => setFormData({...formData, extraTerms: e.target.value})}
                    className="bg-gray-800/60 border-purple-400/30 text-purple-100 focus:border-purple-400 backdrop-blur-sm"
                    placeholder="Additional search terms"
                  />
                </div>
              </div>

              <Button
                onClick={handleSearch}
                disabled={isSearching || !formData.name}
                className="w-full bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-400 hover:to-violet-500 text-white font-bold py-3 rounded-lg transition-all duration-300 transform hover:scale-105 hover:shadow-lg hover:shadow-purple-500/30 border border-purple-400/30 backdrop-blur-sm flex items-center justify-center space-x-2"
              >
                <Search className="w-5 h-5" />
                <span>{isSearching ? 'Searching...' : 'Search'}</span>
              </Button>
            </div>
          </Card>

          {/* Processing Quotes */}
          {isSearching && (
            <Card className="bg-gray-900/60 backdrop-blur-sm border border-purple-400/30 p-8">
              <div className="text-center space-y-4">
                <div className="w-12 h-12 border-2 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <p className="text-purple-200 text-lg italic transition-all duration-1000">
                  "{osintQuotes[currentQuote]}"
                </p>
                <p className="text-purple-300/70">Processing your request...</p>
              </div>
            </Card>
          )}

          {/* Summarizer Results */}
          {hasResults && personData && (
            <Card className="bg-gray-900/60 backdrop-blur-sm border border-purple-400/30 p-8">
              <div className="space-y-6">
                <div className="flex items-center space-x-3">
                  <User className="w-6 h-6 text-purple-400" />
                  <h2 className="text-2xl font-bold text-purple-400">Person Summary</h2>
                </div>
                
                <div className="space-y-4">
                  <div className="bg-purple-400/10 border border-purple-400/30 p-6 rounded-lg backdrop-blur-sm">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                      <div>
                        <h3 className="text-purple-200 font-semibold text-sm uppercase tracking-wide">Name</h3>
                        <p className="text-white text-lg">{personData.name}</p>
                      </div>
                      <div>
                        <h3 className="text-purple-200 font-semibold text-sm uppercase tracking-wide">Location</h3>
                        <p className="text-white text-lg">{personData.location || 'Not specified'}</p>
                      </div>
                      <div>
                        <h3 className="text-purple-200 font-semibold text-sm uppercase tracking-wide">Confidence</h3>
                        <p className="text-green-400 text-lg font-semibold">{personData.confidence}</p>
                      </div>
                      <div>
                        <h3 className="text-purple-200 font-semibold text-sm uppercase tracking-wide">Last Updated</h3>
                        <p className="text-purple-100 text-lg">{personData.lastUpdated}</p>
                      </div>
                    </div>
                    
                    <div>
                      <h3 className="text-purple-200 font-semibold text-sm uppercase tracking-wide mb-3">Summary</h3>
                      <p className="text-purple-100/90 leading-relaxed">
                        {personData.summary}
                      </p>
                    </div>
                  </div>
                </div>

                <Button
                  onClick={handleGenerateReport}
                  className="w-full bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-400 hover:to-violet-500 text-white font-bold py-3 rounded-lg transition-all duration-300 transform hover:scale-105 hover:shadow-lg hover:shadow-purple-500/30 border border-purple-400/30 backdrop-blur-sm flex items-center justify-center space-x-2"
                >
                  <FileText className="w-5 h-5" />
                  <span>Generate Report</span>
                </Button>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default SearchPage;
