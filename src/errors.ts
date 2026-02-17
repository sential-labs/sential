export class SentialError extends Error {
  constructor(
    message: string,
    public readonly internalDetails?: string,
  ) {
    super(message);
    this.name = "SentialError";
    Object.setPrototypeOf(this, SentialError.prototype);
  }
}

export class ProviderError extends SentialError {
  constructor(message: string, internalDetails?: string) {
    super(message, internalDetails);
    this.name = "ProviderError";
    Object.setPrototypeOf(this, ProviderError.prototype);
  }
}
