/**
 * User service for managing user data
 */

export interface User {
  id: number;
  name: string;
  email: string;
  age: number;
}

export class UserService {
  private users: User[] = [
    { id: 1, name: 'Alice', email: 'alice@example.com', age: 30 },
    { id: 2, name: 'Bob', email: 'bob@example.com', age: 25 },
    { id: 3, name: 'Charlie', email: 'charlie@example.com', age: 35 },
  ];

  /**
   * Gets a user by ID
   */
  async getUser(id: number): Promise<User> {
    const user = this.users.find(u => u.id === id);
    if (!user) {
      throw new Error(`User with id ${id} not found`);
    }
    return user;
  }

  /**
   * Gets all users
   */
  async getAllUsers(): Promise<User[]> {
    return [...this.users];
  }

  /**
   * Creates a new user
   */
  async createUser(name: string, email: string, age: number): Promise<User> {
    const newUser: User = {
      id: this.users.length + 1,
      name,
      email,
      age,
    };
    this.users.push(newUser);
    return newUser;
  }

  /**
   * Updates an existing user
   */
  async updateUser(id: number, updates: Partial<User>): Promise<User> {
    const user = await this.getUser(id);
    Object.assign(user, updates);
    return user;
  }

  /**
   * Deletes a user
   */
  async deleteUser(id: number): Promise<void> {
    const index = this.users.findIndex(u => u.id === id);
    if (index === -1) {
      throw new Error(`User with id ${id} not found`);
    }
    this.users.splice(index, 1);
  }
}

