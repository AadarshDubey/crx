"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/layout";
import {
  Card,
  CardContent,
  Button,
  Input,
  Select,
  Modal,
  Spinner,
  Badge,
} from "@/components/ui";
import { SentimentIndicator } from "@/components/sentiment-indicator";
import { accountsApi } from "@/lib/api";
import { TrackedAccount, AccountCategory } from "@/types";
import { cn, formatNumber, formatRelativeTime } from "@/lib/utils";
import {
  Plus,
  Search,
  Trash2,
  RefreshCw,
  ExternalLink,
  AlertCircle,
} from "lucide-react";

const categoryOptions = [
  { value: "influencer", label: "Influencer" },
  { value: "analyst", label: "Analyst" },
  { value: "project", label: "Project" },
  { value: "news", label: "News" },
  { value: "whale", label: "Whale" },
  { value: "developer", label: "Developer" },
  { value: "exchange", label: "Exchange" },
  { value: "vc", label: "VC" },
  { value: "general", label: "General" },
];

const sortOptions = [
  { value: "recent", label: "Most Recent" },
  { value: "tweets", label: "Most Tweets" },
  { value: "sentiment", label: "Sentiment" },
];

export default function AccountsPage() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("recent");
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // Add account form state
  const [newHandle, setNewHandle] = useState("");
  const [newCategory, setNewCategory] = useState<AccountCategory>("influencer");
  const [addError, setAddError] = useState("");

  // Fetch accounts
  const { data: accounts, isLoading, refetch } = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.getAll,
  });

  // Add account mutation
  const addMutation = useMutation({
    mutationFn: accountsApi.add,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      setIsAddModalOpen(false);
      setNewHandle("");
      setNewCategory("influencer");
      setAddError("");
    },
    onError: (error: Error) => {
      console.error("Add account error:", error);
      setAddError(error.message || "Failed to add account");
    },
  });

  // Remove account mutation
  const removeMutation = useMutation({
    mutationFn: accountsApi.remove,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (error: Error) => {
      console.error("Remove account error:", error);
      alert(`Failed to remove account: ${error.message}`);
    },
  });

  // Scrape now mutation
  const scrapeMutation = useMutation({
    mutationFn: accountsApi.scrapeNow,
    onSuccess: () => {
      // Show success feedback
    },
  });

  const handleAddAccount = (e: React.FormEvent) => {
    e.preventDefault();

    if (!newHandle.trim()) {
      setAddError("Please enter a Twitter username");
      return;
    }
    // Remove @ if present
    const handle = newHandle.replace("@", "").trim();
    addMutation.mutate({ handle, category: newCategory });
  };

  const handleRemoveAccount = (handle: string) => {
    if (confirm(`Remove @${handle} from tracking?`)) {
      removeMutation.mutate(handle);
    }
  };

  const handleScrapeNow = (handle: string) => {
    scrapeMutation.mutate(handle);
  };

  // Filter and sort accounts
  const accountsList = Array.isArray(accounts) ? accounts : [];
  const filteredAccounts = accountsList
    .filter((account: TrackedAccount) =>
      account.handle.toLowerCase().includes(searchQuery.toLowerCase()) ||
      account.name?.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a: TrackedAccount, b: TrackedAccount) => {
      switch (sortBy) {
        case "tweets":
          return (b.tweet_count || 0) - (a.tweet_count || 0);
        case "sentiment":
          return (b.avg_sentiment || 0) - (a.avg_sentiment || 0);
        case "recent":
        default:
          return (
            new Date(b.last_scraped_at || b.last_scraped || 0).getTime() -
            new Date(a.last_scraped_at || a.last_scraped || 0).getTime()
          );
      }
    });

  const getSentimentLabel = (score: number): "bullish" | "bearish" | "neutral" => {
    if (score > 0.2) return "bullish";
    if (score < -0.2) return "bearish";
    return "neutral";
  };

  const getCategoryColor = (category: AccountCategory) => {
    switch (category) {
      case "influencer":
        return "bg-primary/20 text-primary";
      case "news":
        return "bg-accent/20 text-accent";
      case "whale":
        return "bg-warning/20 text-warning";
      case "exchange":
        return "bg-bullish/20 text-bullish";
      case "analyst":
        return "bg-blue-500/20 text-blue-400";
      case "project":
        return "bg-purple-500/20 text-purple-400";
      case "developer":
        return "bg-cyan-500/20 text-cyan-400";
      case "vc":
        return "bg-yellow-500/20 text-yellow-400";
      default:
        return "bg-surface-light text-text-secondary";
    }
  };

  return (
    <div className="min-h-screen">
      <Header
        title="Tracked Accounts"
        subtitle={`${accounts?.length || 0} accounts`}
        onRefresh={() => refetch()}
      >
        <Button onClick={() => setIsAddModalOpen(true)} className="gap-2">
          <Plus size={18} />
          Add Account
        </Button>
      </Header>

      <div className="p-6 space-y-6">
        {/* Search & Filter Bar */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="relative flex-1 min-w-[200px]">
                <Search
                  size={18}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
                />
                <Input
                  placeholder="Search accounts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Select
                options={sortOptions}
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Accounts Grid */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : filteredAccounts && filteredAccounts.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredAccounts.map((account: TrackedAccount, index: number) => (
              <Card
                key={account.handle}
                className={cn(
                  "animate-in hover:border-border-light transition-colors",
                  `stagger-${(index % 5) + 1}`
                )}
              >
                <CardContent className="p-4">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                        <span className="text-sm font-bold text-primary">
                          {account.handle[0]?.toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-text-primary">
                            @{account.handle}
                          </span>
                          <a
                            href={`https://twitter.com/${account.handle}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-text-muted hover:text-primary"
                          >
                            <ExternalLink size={12} />
                          </a>
                        </div>
                        {account.name && (
                          <p className="text-xs text-text-muted">
                            {account.name}
                          </p>
                        )}
                      </div>
                    </div>
                    <Badge
                      className={cn(
                        "text-xs capitalize",
                        getCategoryColor(account.category)
                      )}
                    >
                      {account.category.replace("_", " ")}
                    </Badge>
                  </div>

                  {/* Stats */}
                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-sm">
                      <span className="text-text-muted">Tweets:</span>
                      <span className="text-text-primary font-medium">
                        {formatNumber(account.tweet_count || 0)}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-text-muted">Avg Sentiment:</span>
                      <SentimentIndicator
                        sentiment={getSentimentLabel(account.avg_sentiment || 0)}
                        size="sm"
                      />
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-text-muted">Last scraped:</span>
                      <span className="text-text-secondary">
                        {formatRelativeTime(account.last_scraped_at || account.last_scraped || '')}
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 pt-3 border-t border-border">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="flex-1 gap-1.5"
                      onClick={() => handleScrapeNow(account.handle)}
                      disabled={scrapeMutation.isPending}
                    >
                      <RefreshCw
                        size={14}
                        className={cn(
                          scrapeMutation.isPending && "animate-spin"
                        )}
                      />
                      Scrape Now
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-danger hover:bg-danger/10"
                      onClick={() => handleRemoveAccount(account.handle)}
                      disabled={removeMutation.isPending}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-text-muted">
                {searchQuery
                  ? "No accounts found matching your search"
                  : "No accounts being tracked yet"}
              </p>
              <Button
                variant="primary"
                className="mt-4 gap-2"
                onClick={() => setIsAddModalOpen(true)}
              >
                <Plus size={18} />
                Add Your First Account
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Add Account Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => {
          setIsAddModalOpen(false);
          setAddError("");
          setNewHandle("");
        }}
        title="Add Twitter Account"
      >
        <form onSubmit={handleAddAccount} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Twitter Username
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
                @
              </span>
              <Input
                placeholder="username"
                value={newHandle}
                onChange={(e) => {
                  setNewHandle(e.target.value);
                  setAddError("");
                }}
                className="pl-8"
                autoFocus
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Category
            </label>
            <Select
              options={categoryOptions}
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value as AccountCategory)}
              className="w-full"
            />
            <p className="text-xs text-text-muted mt-1">
              {newCategory === "influencer" && "Crypto influencers and thought leaders"}
              {newCategory === "analyst" && "Technical and fundamental analysts"}
              {newCategory === "project" && "Official project accounts"}
              {newCategory === "news" && "News outlets and crypto media"}
              {newCategory === "whale" && "Whale tracking and on-chain alerts"}
              {newCategory === "developer" && "Core developers and builders"}
              {newCategory === "exchange" && "Cryptocurrency exchanges"}
              {newCategory === "vc" && "Venture capital firms"}
              {newCategory === "general" && "General crypto accounts"}
            </p>
          </div>

          {addError && (
            <div className="flex items-center gap-2 text-sm text-danger bg-danger/10 px-3 py-2 rounded-lg">
              <AlertCircle size={16} />
              {addError}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={() => {
                setIsAddModalOpen(false);
                setAddError("");
                setNewHandle("");
              }}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="flex-1"
              disabled={addMutation.isPending || !newHandle.trim()}
            >
              {addMutation.isPending ? (
                <>
                  <Spinner size="sm" className="mr-2" />
                  Adding...
                </>
              ) : (
                "Add Account"
              )}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
