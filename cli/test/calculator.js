/**
 * Calculator class for basic arithmetic operations (JavaScript version)
 */

class Calculator {
  constructor() {
    this.history = [];
  }

  /**
   * Adds two numbers
   */
  add(a, b) {
    const result = a + b;
    this.history.push(result);
    return result;
  }

  /**
   * Subtracts b from a
   */
  subtract(a, b) {
    const result = a - b;
    this.history.push(result);
    return result;
  }

  /**
   * Multiplies two numbers
   */
  multiply(a, b) {
    const result = a * b;
    this.history.push(result);
    return result;
  }

  /**
   * Divides a by b
   */
  divide(a, b) {
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
  getHistory() {
    return [...this.history];
  }

  /**
   * Clears calculation history
   */
  clearHistory() {
    this.history = [];
  }
}

module.exports = { Calculator };

