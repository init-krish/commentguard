/**
 * CommentGuard SDK Configuration
 */
export interface CommentGuardConfig {
  /**
   * The base URL of your self-hosted CommentGuard API.
   * @default "http://localhost:8000"
   */
  endpoint?: string;
  
  /**
   * Optional API key if your CommentGuard instance is behind an auth gateway.
   */
  apiKey?: string;
}

export interface ModerateOptions {
  /**
   * Override the default toxicity threshold (0.0 - 1.0).
   * Probabilities above this threshold will trigger a "block" decision.
   */
  threshold?: number;
  
  /**
   * Optional site identifier (e.g. "youtube", "reddit") for context-aware rules or analytics.
   */
  site?: string;
}

export interface CategoryScores {
  toxic: number;
  severe_toxic: number;
  obscene: number;
  threat: number;
  insult: number;
  identity_hate: number;
}

export interface ModerateResponse {
  label: "toxic" | "non_toxic";
  toxic_prob: number;
  decision: "allow" | "review" | "block";
  categories: Array<keyof CategoryScores>;
  scores: CategoryScores;
  flagged: boolean;
}

export interface BatchResponse {
  results: ModerateResponse[];
  total: number;
  toxic_count: number;
  processing_time_ms: number;
}

export interface StatsResponse {
  total: number;
  toxic: number;
  non_toxic: number;
  toxic_rate: number;
  by_category: Record<string, number>;
  model: string;
  version: string;
  recent: any[];
}

export class CommentGuardError extends Error {
  public status?: number;
  
  constructor(message: string, status?: number) {
    super(message);
    this.name = "CommentGuardError";
    this.status = status;
  }
}

/**
 * CommentGuard Node.js SDK
 * 
 * @example
 * const guard = new CommentGuard({ endpoint: "https://api.yourdomain.com" });
 * const result = await guard.moderate("You are terrible!");
 * if (result.decision === "block") { ... }
 */
export class CommentGuard {
  private endpoint: string;
  private headers: Record<string, string>;

  constructor(config: CommentGuardConfig = {}) {
    // Remove trailing slashes
    this.endpoint = (config.endpoint || "http://localhost:8000").replace(/\/$/, "");
    
    this.headers = {
      "Content-Type": "application/json",
      "User-Agent": "commentguard-node-sdk/1.0"
    };

    if (config.apiKey) {
      this.headers["Authorization"] = `Bearer ${config.apiKey}`;
      this.headers["X-API-Key"] = config.apiKey;
    }
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.endpoint}${path}`;
    const response = await fetch(url, {
      ...options,
      headers: { ...this.headers, ...options.headers }
    });

    if (!response.ok) {
      let errorMsg = `API request failed: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMsg = Array.isArray(errorData.detail) 
            ? errorData.detail.map((e: any) => e.msg).join(", ")
            : errorData.detail;
        }
      } catch (e) {
        // Fallback if not JSON
      }
      throw new CommentGuardError(errorMsg, response.status);
    }

    return response.json() as Promise<T>;
  }

  /**
   * Moderate a single text comment.
   */
  public async moderate(text: string, options: ModerateOptions = {}): Promise<ModerateResponse> {
    if (!text || text.trim() === "") {
      throw new CommentGuardError("Text cannot be empty");
    }

    return this.request<ModerateResponse>("/moderate", {
      method: "POST",
      body: JSON.stringify({
        text,
        threshold: options.threshold,
        site: options.site
      })
    });
  }

  /**
   * Moderate up to 100 texts in a single batch request.
   */
  public async moderateBatch(texts: string[], options: ModerateOptions = {}): Promise<BatchResponse> {
    if (!texts || texts.length === 0) {
      throw new CommentGuardError("Texts array cannot be empty");
    }
    if (texts.length > 100) {
      throw new CommentGuardError("Maximum 100 texts allowed per batch request");
    }

    return this.request<BatchResponse>("/moderate/batch", {
      method: "POST",
      body: JSON.stringify({
        texts,
        threshold: options.threshold,
        site: options.site
      })
    });
  }

  /**
   * Submit false positive or false negative feedback to improve the model.
   */
  public async submitFeedback(text: string, correctLabel: "toxic" | "non_toxic", predictedLabel: "toxic" | "non_toxic"): Promise<{ status: string }> {
    return this.request<{ status: string }>("/feedback", {
      method: "POST",
      body: JSON.stringify({
        text,
        correct_label: correctLabel,
        predicted_label: predictedLabel
      })
    });
  }

  /**
   * Get live analytics and health stats from the server.
   */
  public async getStats(): Promise<StatsResponse> {
    return this.request<StatsResponse>("/stats", {
      method: "GET"
    });
  }

  /**
   * Check if the CommentGuard server is reachable and healthy.
   */
  public async healthCheck(): Promise<boolean> {
    try {
      await this.request("/health", { method: "GET" });
      return true;
    } catch (e) {
      return false;
    }
  }
}
