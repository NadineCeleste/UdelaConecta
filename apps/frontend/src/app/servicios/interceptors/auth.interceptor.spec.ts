import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';

import { authInterceptor } from './auth.interceptor';
import { AuthService } from '../AuthService';
import { environment } from '../../environments/environment';

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('auth_token', 'token-de-prueba');
    localStorage.setItem('auth_user', JSON.stringify({ id: '1', email: 'dev@udela.edu.ar' }));
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        provideRouter([])
      ]
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('agrega el token a las llamadas a la API', () => {
    http.get(`${environment.apiUrl}contratos`).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}contratos`);
    expect(req.request.headers.get('Authorization')).toBe('Bearer token-de-prueba');
    req.flush({ data: [] });
  });

  it('no manda el token a otros dominios', () => {
    http.get('https://ejemplo.com/datos').subscribe();
    const req = httpMock.expectOne('https://ejemplo.com/datos');
    expect(req.request.headers.has('Authorization')).toBeFalse();
    req.flush({});
  });

  it('cierra la sesión si la API responde 401', () => {
    const auth = TestBed.inject(AuthService);
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    http.get(`${environment.apiUrl}contratos`).subscribe({ error: () => {} });
    httpMock.expectOne(`${environment.apiUrl}contratos`).flush({}, { status: 401, statusText: 'Unauthorized' });
    expect(auth.getToken()).toBeNull();
    expect(navigate).toHaveBeenCalledWith(['/']);
  });
});
