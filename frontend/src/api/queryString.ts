export type QueryPrimitive = string | number | boolean;
export type QueryValue = QueryPrimitive | null | undefined;

export function appendArrayParam(
  params: URLSearchParams,
  key: string,
  values?: readonly QueryPrimitive[] | null
): void {
  values?.forEach((value) => {
    params.append(key, String(value));
  });
}

export function appendOptionalParam(
  params: URLSearchParams,
  key: string,
  value?: QueryValue
): void {
  if (value === undefined || value === null || value === "") {
    return;
  }

  params.append(key, String(value));
}

export function appendOptionalNumber(
  params: URLSearchParams,
  key: string,
  value?: number | null
): void {
  if (value === undefined || value === null) {
    return;
  }

  params.append(key, value.toString());
}

export function appendOptionalJson(
  params: URLSearchParams,
  key: string,
  value?: Record<string, unknown> | null
): void {
  if (!value || Object.keys(value).length === 0) {
    return;
  }

  params.set(key, JSON.stringify(value));
}

export function buildQueryString(params: URLSearchParams): string {
  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
}

export function createSearchParams(
  populate: (params: URLSearchParams) => void
): URLSearchParams {
  const params = new URLSearchParams();
  populate(params);
  return params;
}

export function buildFormUrlEncoded(
  values: Record<string, QueryPrimitive | null | undefined>
): URLSearchParams {
  return createSearchParams((params) => {
    Object.entries(values).forEach(([key, value]) => {
      appendOptionalParam(params, key, value);
    });
  });
}
