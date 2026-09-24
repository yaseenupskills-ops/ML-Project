import { User } from '../lib/store';

export async function loginStub(email: string, _password: string):Promise<User> {
  const bypass = process.env.NEXT_PUBLIC_DEV_AUTH_BYPASS === 'true';
  if (bypass) {
    return {
      id: 'dev-1',
      name: 'Dev Admin',
      email: email,
      role: 'admin',
    };
  }
  throw new Error("Backend not connected");
}
