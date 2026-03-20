import { apiFetchBlob } from "./client";

export type ExportType = "entities" | "relations" | "sources" | "full-graph";

function getExportPath(
  exportType: ExportType,
  format: string,
  params?: Record<string, string | number | string[] | undefined | null>,
): string {
  const basePath = `/export/${exportType}`;
  if (exportType === "full-graph") return basePath;

  const qs = new URLSearchParams();
  qs.set("format", format);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null) continue;
      if (Array.isArray(value)) {
        value.forEach((v) => qs.append(key, String(v)));
      } else {
        qs.set(key, String(value));
      }
    }
  }
  return `${basePath}?${qs.toString()}`;
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
  params?: Record<string, string | number | string[] | undefined | null>,
): Promise<string> {
  const response = await apiFetchBlob(getExportPath(exportType, format, params), {
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
