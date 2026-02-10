export class SentialError extends Error {
  constructor(
    message: string,
    public readonly internalDetails?: string,
  ) {
    super(message);
    this.name = "SentialError";
  }
}

export class ProviderError extends SentialError {
  constructor(
    message: string,
    public readonly internalDetails?: string,
  ) {
    super(message);
    this.name = "ProviderError";
  }
}
