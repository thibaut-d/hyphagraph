export interface SourceRead {
  id: string;
  kind: string;
  title: string;
  year: number;
  origin?: string | null;
  url?: string | null;
  trust_level: number;
}

export interface SourceWrite {
  kind: string;
  title: string;
  year: number;
  origin?: string | null;
  url?: string | null;
  trust_level: number;
}
