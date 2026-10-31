import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { environment } from '../environments/environment';

export interface ChatResponse {
  message: string;
  data: { respuesta: string };
}

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private _apiUrl = environment.apiUrl;

  constructor(private _httpClient: HttpClient) {}

  // El backend decide si responde el asistente de invitados o el de usuarios a partir del
  // token (lo agrega authInterceptor); el front solo manda el mensaje y la conversación
  enviar(mensaje: string, sessionId: string): Observable<string> {
    return this._httpClient
      .post<ChatResponse>(this._apiUrl + 'chat', { mensaje, session_id: sessionId })
      .pipe(map((res) => res.data.respuesta));
  }
}
