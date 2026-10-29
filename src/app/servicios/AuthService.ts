import { Injectable } from '@angular/core';
import { BehaviorSubject, distinctUntilChanged, map } from 'rxjs';

// Versión simulada (sin Supabase ni backend) para poder levantar el frontend.
export interface User {
  id: string;
  email: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private userSubject = new BehaviorSubject<User | null>(this.loadStored());

  user$ = this.userSubject.asObservable();
  userEmail$ = this.user$.pipe(
    map(u => u?.email ?? null),
    distinctUntilChanged()
  );

  get session(): Promise<{ data: { session: { user: User } | null } }> {
    const user = this.userSubject.value;
    return Promise.resolve({ data: { session: user ? { user } : null } });
  }

  async signIn(email: string, _password: string) {
    const user = this.setUser(email);
    return { data: { user, session: { user } }, error: null as any };
  }

  async signUp(email: string, _password: string) {
    const user = this.setUser(email);
    return { data: { user, session: { user } }, error: null as any };
  }

  async signInWithSocial(_provider: string) {
    const user = this.setUser('demo@udelar.test');
    return { data: { user, session: { user } }, error: null as any };
  }

  async resetPassword(_email: string) {
    return { error: null as any };
  }

  async signOut() {
    localStorage.removeItem('mock_user');
    this.userSubject.next(null);
  }

  private setUser(email: string): User {
    const user = { id: email, email };
    localStorage.setItem('mock_user', JSON.stringify(user));
    this.userSubject.next(user);
    return user;
  }

  private loadStored(): User | null {
    try {
      return JSON.parse(localStorage.getItem('mock_user') ?? 'null');
    } catch {
      return null;
    }
  }
}
