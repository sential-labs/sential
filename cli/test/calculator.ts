/**
 * Calculator class for basic arithmetic operations
 */

export class Calculator {
  private history: number[] = [];

  /**
   * Adds two numbers
   */
  add(a: number, b: number): number {
    const result = a + b;
    this.history.push(result);
    return result;
  }

  /**
   * Subtracts b from a
   */
  subtract(a: number, b: number): number {
    const result = a - b;
    this.history.push(result);
    return result;
  }

  /**
   * Multiplies two numbers
   */
  multiply(a: number, b: number): number {
    const result = a * b;
    this.history.push(result);
    return result;
  }

  /**
   * Divides a by b
   */
  divide(a: number, b: number): number {
    if (b === 0) {
      throw new Error('Division by zero');
    }
    const result = a / b;
    this.history.push(result);
    return result;
  }

  /**
   * Gets calculation history
   */
  getHistory(): number[] {
    return [...this.history];
  }

  /**
   * Clears calculation history
   */
  clearHistory(): void {
    this.history = [];
  }
}

