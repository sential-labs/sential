/**
 * Data processing utilities
 */

/**
 * Processes an array of numbers
 */
function processData(data) {
  return data
    .filter(item => item > 0)
    .map(item => item * 2)
    .sort((a, b) => a - b);
}

/**
 * Calculates the sum of an array
 */
function sum(numbers) {
  return numbers.reduce((acc, num) => acc + num, 0);
}

/**
 * Calculates the average of an array
 */
function average(numbers) {
  if (numbers.length === 0) {
    return 0;
  }
  return sum(numbers) / numbers.length;
}

/**
 * Finds the maximum value in an array
 */
function max(numbers) {
  if (numbers.length === 0) {
    return null;
  }
  return Math.max(...numbers);
}

/**
 * Finds the minimum value in an array
 */
function min(numbers) {
  if (numbers.length === 0) {
    return null;
  }
  return Math.min(...numbers);
}

module.exports = {
  processData,
  sum,
  average,
  max,
  min,
};

