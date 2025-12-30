/**
 * Alternative main entry point in JavaScript
 */

const { Calculator } = require('./calculator');
const { processData } = require('./test2/dataProcessor');
const config = require('../test3/config');

function runApp() {
  console.log('Starting application...');
  console.log(`Environment: ${config.get('environment')}`);

  // Use calculator
  const calc = new Calculator();
  const result = calc.multiply(5, 6);
  console.log(`5 * 6 = ${result}`);

  // Use data processor from test2
  const data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  const processed = processData(data);
  console.log(`Processed: ${processed.join(', ')}`);

  console.log('Application completed');
}

if (require.main === module) {
  runApp();
}

module.exports = { runApp };

