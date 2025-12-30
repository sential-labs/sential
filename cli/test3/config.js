/**
 * Configuration management
 */

class Config {
  constructor() {
    this.settings = {
      apiUrl: process.env.API_URL || 'https://api.example.com',
      port: parseInt(process.env.PORT || '3000', 10),
      environment: process.env.NODE_ENV || 'development',
      debug: process.env.DEBUG === 'true',
    };
  }

  /**
   * Gets a configuration value
   */
  get(key) {
    return this.settings[key];
  }

  /**
   * Sets a configuration value
   */
  set(key, value) {
    this.settings[key] = value;
  }

  /**
   * Gets all configuration
   */
  getAll() {
    return { ...this.settings };
  }

  /**
   * Checks if running in development mode
   */
  isDevelopment() {
    return this.settings.environment === 'development';
  }

  /**
   * Checks if running in production mode
   */
  isProduction() {
    return this.settings.environment === 'production';
  }
}

const config = new Config();

module.exports = config;

