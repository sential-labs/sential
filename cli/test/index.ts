/**
 * Main entry point for the application
 */

import { Calculator } from './calculator';
import { UserService } from './services/userService';
import { formatCurrency } from './utils/formatters';
import { processData } from './test2/dataProcessor';
import { Logger } from '../test3/logger';

const logger = new Logger('MainApp');

async function main() {
  logger.info('Application starting...');

  // Use calculator from same directory
  const calc = new Calculator();
  const result = calc.add(10, 20);
  console.log(`Calculation result: ${result}`);

  // Use service from same directory
  const userService = new UserService();
  const user = await userService.getUser(1);
  console.log(`User: ${user.name}`);

  // Use formatter from same directory
  const price = formatCurrency(99.99);
  console.log(`Price: ${price}`);

  // Use processor from test2
  const processed = processData([1, 2, 3, 4, 5]);
  console.log(`Processed data: ${processed.join(', ')}`);

  logger.info('Application completed');
}

main().catch(console.error);

