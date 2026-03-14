import { useCallback, useState } from "react";

export function useValidationMessage<TField extends string = string>() {
  const [validationMessage, setValidationMessageState] = useState<string | null>(null);
  const [validationField, setValidationField] = useState<TField | null>(null);

  const setValidationMessage = useCallback((message: string | null, field?: TField | null) => {
    setValidationMessageState(message);
    setValidationField(message ? (field ?? null) : null);
  }, []);

  const clearValidationMessage = useCallback((field?: TField) => {
    if (field && validationField && validationField !== field) {
      return;
    }
    setValidationMessageState(null);
    setValidationField(null);
  }, [validationField]);

  const getFieldError = useCallback((field: TField) => {
    return validationField === field ? validationMessage : null;
  }, [validationField, validationMessage]);

  const hasFieldError = useCallback((field: TField) => {
    return validationField === field && Boolean(validationMessage);
  }, [validationField, validationMessage]);

  return {
    validationMessage,
    validationField,
    setValidationMessage,
    clearValidationMessage,
    getFieldError,
    hasFieldError,
  };
}
