/** Browser-only Supabase Auth REST client. Never includes a database password or service role key. */
const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined;

export const supabaseConfigured = Boolean(url && key);

type AuthSession = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
};

async function request(path: string, body: unknown): Promise<Record<string, unknown>> {
  if (!url || !key) throw new Error('Supabase Auth is not configured for this website.');
  let response: Response;
  try {
    response = await fetch(url.replace(/\/$/, '') + '/auth/v1/' + path, {
      method: 'POST',
      headers: { apikey: key, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store',
    });
  } catch {
    throw new Error('Cannot reach the sign-in service. Check your connection.');
  }
  const payload: Record<string, unknown> = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload.msg || payload.error_description || payload.message || payload.error;
    throw new Error(typeof message === 'string' ? message : 'Sign-in failed. Please retry.');
  }
  return payload;
}

function sessionOf(payload: Record<string, unknown>): AuthSession | null {
  if (typeof payload.access_token !== 'string' || typeof payload.refresh_token !== 'string') return null;
  return { access_token: payload.access_token, refresh_token: payload.refresh_token, expires_in: Number(payload.expires_in) || 3600 };
}

export async function signIn(email: string, password: string): Promise<AuthSession> {
  const session = sessionOf(await request('token?grant_type=password', { email, password }));
  if (!session) throw new Error('No session was returned. Please confirm your email address.');
  return session;
}

export async function signUp(email: string, password: string): Promise<AuthSession | null> {
  return sessionOf(await request('signup', { email, password }));
}

export async function refreshSession(refresh_token: string): Promise<AuthSession> {
  const session = sessionOf(await request('token?grant_type=refresh_token', { refresh_token }));
  if (!session) throw new Error('Session renewal failed. Please sign in again.');
  return session;
}
