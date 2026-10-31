import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { ChatService } from './chat.service';
import { environment } from '../environments/environment';

describe('ChatService', () => {
  let service: ChatService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ChatService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('manda el mensaje y la sesión, y devuelve solo la respuesta', () => {
    let respuesta = '';
    service.enviar('¿Cómo me registro?', 'sesion-1').subscribe((r) => (respuesta = r));

    const req = http.expectOne(environment.apiUrl + 'chat');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ mensaje: '¿Cómo me registro?', session_id: 'sesion-1' });
    req.flush({ message: 'ok', data: { respuesta: 'Tocá Registrate' } });

    expect(respuesta).toBe('Tocá Registrate');
  });
});
