"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import { ExternalLink, Clock, Newspaper } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface Article {
  id: number;
  title: string;
  url: string;
  source_id: string;
  source_name: string;
  published_at: string;
  summary?: string;
  image_url?: string;
  category?: string;
}

interface LatestArticlesProps {
  articles: Article[];
  title?: string;
}

function getSourceColor(sourceId: string): string {
  const colors: Record<string, string> = {
    coindesk: "bg-blue-500",
    cointelegraph: "bg-green-500",
    decrypt: "bg-purple-500",
    theblock: "bg-orange-500",
    bitcoinmagazine: "bg-amber-500",
  };
  return colors[sourceId] || "bg-gray-500";
}

function ArticleCard({ article }: { article: Article }) {
  const timeAgo = article.published_at
    ? formatDistanceToNow(new Date(article.published_at), { addSuffix: true })
    : "Unknown time";

  return (
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block p-3 rounded-lg bg-card-hover/50 hover:bg-card-hover transition-colors group"
    >
      <div className="flex items-start gap-3">
        <div className={`w-1 h-full min-h-[60px] rounded-full ${getSourceColor(article.source_id)}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs px-2 py-0.5 rounded-full ${getSourceColor(article.source_id)} text-white`}>
              {article.source_name || article.source_id}
            </span>
            {article.category && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-card-hover text-muted">
                {article.category}
              </span>
            )}
          </div>
          <h3 className="text-sm font-medium line-clamp-2 group-hover:text-primary transition-colors">
            {article.title}
          </h3>
          {article.summary && (
            <p className="text-xs text-muted mt-1 line-clamp-2">{article.summary}</p>
          )}
          <div className="flex items-center gap-2 mt-2 text-xs text-muted">
            <Clock size={12} />
            <span>{timeAgo}</span>
            <ExternalLink size={12} className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>
      </div>
    </a>
  );
}

export function LatestArticles({ articles, title = "Latest News" }: LatestArticlesProps) {
  return (
    <Card className="bg-surface/30 backdrop-blur-md border-white/5 shadow-glass">
      <CardHeader className="pb-4 border-b border-white/5">
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
          <Newspaper size={14} className="text-primary" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-white/10 hover:scrollbar-thumb-white/20 pt-4">
          {articles.length > 0 ? (
            articles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))
          ) : (
            <p className="text-muted text-sm text-center py-8 italic">
              No articles available. Try scraping news first.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
