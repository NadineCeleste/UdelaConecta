import { Injectable} from '@angular/core';
import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { Contrato, ContratoResponse, PostulacionResponse } from '../models/contrato';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ContratoService {
  private _contratosUrl = environment.apiUrl;


  constructor(private _httpClient: HttpClient) { }

  getContratos(): Observable<ContratoResponse> {
    const res = this._httpClient.get<ContratoResponse>(this._contratosUrl + 'contratos');
    return res
  }

  //trae los contratos esta_ocupado = false para los devs
  getContratosLibres(): Observable<ContratoResponse> {
    const res = this._httpClient.get<ContratoResponse>(this._contratosUrl + 'contratoslibres');
    return res
  }

  //trae los contratos por email gerente
  getContratosByEmailGerente(emailGerente:string): Observable<ContratoResponse> {
    const res = this._httpClient.get<ContratoResponse>(`${this._contratosUrl}contratos/${emailGerente}`);
    return res
  }

  postContrato(contrato: Contrato): Observable<ContratoResponse> {
    const req = contrato;
    const res = this._httpClient.post<ContratoResponse>(this._contratosUrl + 'contrato', req)
    return res
  }

  updateContrato(contrato: Contrato): Observable<PostulacionResponse> {
    const req = contrato;
    const res = this._httpClient.put<PostulacionResponse>(`${this._contratosUrl}contrato/${contrato.id}`, req)
    return res
  }
  
  postularseAContrato(id:string, email:string): Observable<PostulacionResponse> {
    //console.log('intentando update de Postulacion id ',id.toString(), 'sumando la postulación de ',email )
    const res = this._httpClient.put<PostulacionResponse>(this._contratosUrl + 'contrato/' + id, {"postulaciones" : email});
    return res
  }

  asignarPostulante(idContrato: string, email: string): Observable<ContratoResponse> {
    const body = { pasante_email: email };
    return this._httpClient.put<ContratoResponse>(
      `${this._contratosUrl}contrato/asignar/${idContrato}`,
      body
    );
  }

  deleteContrato(id: string): Observable<any> {
    return this._httpClient.delete(`${this._contratosUrl}contrato/${id}`);
  }

}
