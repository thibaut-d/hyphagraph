const configuredSiteName = import.meta.env.VITE_SITE_NAME?.trim();

export const siteDisplayName =
  configuredSiteName && configuredSiteName.length > 0
    ? configuredSiteName
    : "HyphaGraph";
