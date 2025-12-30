/**
 * API client for making HTTP requests
 */

class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Content-Type': 'application/json',
    };
  }

  /**
   * Makes a GET request
   */
  async get(endpoint) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'GET',
      headers: this.headers,
    });
    return response.json();
  }

  /**
   * Makes a POST request
   */
  async post(endpoint, data) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(data),
    });
    return response.json();
  }

  /**
   * Makes a PUT request
   */
  async put(endpoint, data) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'PUT',
      headers: this.headers,
      body: JSON.stringify(data),
    });
    return response.json();
  }

  /**
   * Makes a DELETE request
   */
  async delete(endpoint) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'DELETE',
      headers: this.headers,
    });
    return response.json();
  }

  /**
   * Sets an authorization header
   */
  setAuthToken(token) {
    this.headers['Authorization'] = `Bearer ${token}`;
  }
}

module.exports = { ApiClient };

