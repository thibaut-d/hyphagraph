import { apiFetchBlob } from "./client";

export type ExportType = "entities" | "relations" | "sources" | "full-graph";

function getExportPath(exportType: ExportType, format: string): string {
  const basePath = `/export/${exportType}`;
  return exportType === "full-graph"
    ? basePath
    : `${basePath}?format=${encodeURIComponent(format)}`;
}

function getFilenameFromDisposition(
  disposition: string | null,
  exportType: ExportType,
  format: string,
): string {
  const match = disposition?.match(/filename="(.+)"/);
  if (match?.[1]) {
    return match[1];
  }

  return `${exportType}-export.${format}`;
}

export async function downloadExportFile(
  exportType: ExportType,
  format: string,
): Promise<string> {
  const response = await apiFetchBlob(getExportPath(exportType, format), {
    method: "GET",
  });

  const filename = getFilenameFromDisposition(
    response.headers.get("Content-Disposition"),
    exportType,
    format,
  );
  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(downloadUrl);

  return filename;
}
