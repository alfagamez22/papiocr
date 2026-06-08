export interface TranslateTextRequest {
  text: string;
  source: string;
  target: string;
}

export interface TranslateTextResponse {
  source: string;
  target: string;
  original: string;
  translated: string;
}

export interface LanguageList {
  languages: string[];
  shortcuts: Record<string, string>;
}

export interface HealthResponse {
  status: string;
  version: string;
}
