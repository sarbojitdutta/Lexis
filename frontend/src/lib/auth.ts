const TOKEN_KEY = "lexis_token"
export interface User{
    email : string,
    name : string,
    picture : string
}

export function saveToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token)
}
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function parseToken(token: string): User | null {
  try {
    const payload = token.split(".")[1];
    const decoded = JSON.parse(atob(payload));
    return {
      email  : decoded.email   || "",
      name   : decoded.name    || "",
      picture: decoded.picture || "",
    };
  } catch {
    return null;
  }
}

export function getCurrentUser(): User | null {
  const token = getToken();
  if (!token) return null;
  return parseToken(token);
}

export function loginWithGoogle(): void {
  window.location.href = "http://localhost:8000/api/auth/google";
}

export function logout(): void {
  removeToken();
  window.location.reload();
}

export function handleOAuthRedirect(): boolean {
  const params = new URLSearchParams(window.location.search);
  const token  = params.get("token");
  if (token) {
    saveToken(token);
    // Clean token from URL
    window.history.replaceState({}, "", window.location.pathname);
    return true;
  }
  return false;
}