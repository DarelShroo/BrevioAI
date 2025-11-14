export interface ModelTypeResponse {
  [key: string]: string;
}

export interface LanguageTypeResponse {
  [key: string]: string;
}

export interface SummaryLevelResponse {
  [key: string]: string;
}

export interface OutputFormatResponse {
  [key: string]: string;
}

export interface CategoryOptions {
  [key: string]: string;
}

export interface StyleOptions {
  [key: string]: string;
}

export interface OutputFormatOptions {
  [key: string]: string;
}

interface StyleConfiguration {
  style: string;
  source_types: string[];
}

export interface AdvancedContentCombinations {
  [category: string]: StyleConfiguration[];
}
