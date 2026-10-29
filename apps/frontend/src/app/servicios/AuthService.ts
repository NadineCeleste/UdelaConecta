import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, distinctUntilChanged, firstValueFrom, map } from 'rxjs';
import { environment } from '../environments/environment';

// Autenticación contra la API propia (/api/auth/*) con JWT.
// Mantiene la misma interfaz pública que el servicio original.
export interface User {
  id: string;
  email: string;
  // Lo define el backend (auth_users.is_admin); registrarse con un email no lo activa
  is_admin?: boolean;
}

interface AuthError {
  message: string;
  error_description?: string;
}

interface AuthApiResponse {
  data: {
    user: User | null;
    session: { user: User; access_token: string } | null;
  };
  error: AuthError | null;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly STORAGE_USER_KEY = 'auth_user';
  private readonly STORAGE_TOKEN_KEY = 'auth_token';
  private userSubject = new BehaviorSubject<User | null>(this.loadStored());

  user$ = this.userSubject.asObservable();
  userEmail$ = this.user$.pipe(
    map(u => u?.email ?? null),
    distinctUntilChanged()
  );

  constructor(private http: HttpClient) {}

  get session(): Promise<{ data: { session: { user: User } | null } }> {
    const user = this.userSubject.value;
    const token = this.getToken();
    return Promise.resolve({ data: { session: user && token ? { user } : null } });
  }

  getToken(): string | null {
    try {
      return localStorage.getItem(this.STORAGE_TOKEN_KEY);
    } catch {
      return null;
    }
  }

  async signIn(email: string, password: string) {
    return this.autenticar('auth/login', { email, password }, 'Error al iniciar sesión');
  }

  async signUp(email: string, password: string) {
    return this.autenticar('auth/register', { email, password }, 'Hubo problemas al crear tu cuenta');
  }

  async signInWithSocial(provider: string) {
    return this.autenticar('auth/social', { provider }, 'Error en el inicio de sesión social');
  }

  async resetPassword(email: string) {
    try {
      await firstValueFrom(this.http.post(`${environment.apiUrl}auth/reset-password`, { email }));
      return { error: null as any };
    } catch (err: any) {
      return { error: { message: this.mensajeDeError(err, 'No se pudo enviar el correo') } };
    }
  }

  async signOut() {
    localStorage.removeItem(this.STORAGE_USER_KEY);
    localStorage.removeItem(this.STORAGE_TOKEN_KEY);
    localStorage.removeItem('mock_user'); // restos de la versión simulada
    this.userSubject.next(null);
  }

  private async autenticar(ruta: string, body: object, mensajePorDefecto: string) {
    try {
      const res = await firstValueFrom(
        this.http.post<AuthApiResponse>(`${environment.apiUrl}${ruta}`, body)
      );
      if (res.error || !res.data.user || !res.data.session) {
        const error = res.error ?? { message: mensajePorDefecto };
        return { data: { user: null, session: null }, error: error as any };
      }
      this.persistSession(res.data.user, res.data.session.access_token);
      return { data: res.data, error: null as any };
    } catch (err: any) {
      const msg = this.mensajeDeError(err, mensajePorDefecto);
      return {
        data: { user: null, session: null },
        error: { message: msg, error_description: msg } as any
      };
    }
  }

  private mensajeDeError(err: any, mensajePorDefecto: string): string {
    const detail = err?.error?.detail;
    if (typeof detail === 'string') return detail;
    return err?.error?.error?.message || mensajePorDefecto;
  }

  private persistSession(user: User, token: string): void {
    localStorage.setItem(this.STORAGE_USER_KEY, JSON.stringify(user));
    localStorage.setItem(this.STORAGE_TOKEN_KEY, token);
    this.userSubject.next(user);
  }

  private loadStored(): User | null {
    try {
      if (!localStorage.getItem(this.STORAGE_TOKEN_KEY)) return null;
      return JSON.parse(localStorage.getItem(this.STORAGE_USER_KEY) ?? 'null');
    } catch {
      return null;
    }
  }
}
