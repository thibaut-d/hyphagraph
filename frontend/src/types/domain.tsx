export interface Source {
  id: string;
  kind: string;
  title: string;
  year: number;
}

export interface Entity {
  id: string;
  kind: string;
  label: string;
}

export interface Relation {
  id: string;
  kind: string;
  direction: "positive" | "negative" | "null" | "mixed";
}

export interface Inference {
  id: string;
  result: unknown;
  uncertainty?: number;
}