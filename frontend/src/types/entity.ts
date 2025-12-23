export interface EntityRead {
  id: string;
  kind: string;
  label: string;
  label_i18n?: Record<string, string>;
}