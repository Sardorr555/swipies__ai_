import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle2, Sparkles, Target, TrendingUp } from 'lucide-react';

export interface GuideTabProps {
  // Pure presentation component with zero external state dependencies
}

export const GuideTab: React.FC<GuideTabProps> = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-blue-500" /> The Swipies Ads Principles
        </CardTitle>
        <CardDescription>
          How native AI intent recommendations work without spamming users or sacrificing answer quality.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-muted-foreground leading-relaxed">
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border p-4 bg-muted/20">
            <div className="font-semibold text-foreground flex items-center gap-2 mb-2">
              <Target className="h-4 w-4 text-blue-500" /> 1. Intent & Semantic Matching
            </div>
            <p className="text-xs">
              Your ad only participates in the auction when a user asks a question directly relevant to your product category. If the query is unrelated, no ad is forced.
            </p>
          </div>

          <div className="rounded-lg border p-4 bg-muted/20">
            <div className="font-semibold text-foreground flex items-center gap-2 mb-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" /> 2. Transparent & Non-Intrusive
            </div>
            <p className="text-xs">
              Recommendations are explicitly labeled with <span className="font-bold text-foreground">[Sponsored]</span> and separated from the main AI answer.
            </p>
          </div>

          <div className="rounded-lg border p-4 bg-muted/20">
            <div className="font-semibold text-foreground flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-purple-500" /> 3. Performance Driven (CPC/CPM)
            </div>
            <p className="text-xs">
              Pay only when interested users engage or visit your landing page. Set strict daily budgets to control costs with 100% transparency.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default GuideTab;
