/**
 * Logger utility for application logging
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

export class Logger {
  private context: string;
  private level: LogLevel;

  constructor(context: string, level: LogLevel = LogLevel.INFO) {
    this.context = context;
    this.level = level;
  }

  /**
   * Logs a debug message
   */
  debug(message: string, ...args: any[]): void {
    if (this.level <= LogLevel.DEBUG) {
      console.debug(`[DEBUG] [${this.context}]`, message, ...args);
    }
  }

  /**
   * Logs an info message
   */
  info(message: string, ...args: any[]): void {
    if (this.level <= LogLevel.INFO) {
      console.info(`[INFO] [${this.context}]`, message, ...args);
    }
  }

  /**
   * Logs a warning message
   */
  warn(message: string, ...args: any[]): void {
    if (this.level <= LogLevel.WARN) {
      console.warn(`[WARN] [${this.context}]`, message, ...args);
    }
  }

  /**
   * Logs an error message
   */
  error(message: string, ...args: any[]): void {
    if (this.level <= LogLevel.ERROR) {
      console.error(`[ERROR] [${this.context}]`, message, ...args);
    }
  }

  /**
   * Sets the log level
   */
  setLevel(level: LogLevel): void {
    this.level = level;
  }
}

