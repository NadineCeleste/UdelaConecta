import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { Users } from './users';
import { Proyecto, ProyectoResponse } from '../models/proyectos';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class ProyectoService {
  private _proyectosUrl = environment.apiUrl;

  private _usersService = inject(Users);
  user: any;
  rol: any;

  constructor(private _httpClient: HttpClient) { }

 /*  ngOnInit(): void {
    this.loadUser();
  } */


  getProyectoPorEmail(email:string): Observable<ProyectoResponse> {
    /* console.log('buscando proyecto de ',email) */
    const res = this._httpClient.get<ProyectoResponse>(this._proyectosUrl + 'proyecto/' + email);
    return res
  }

  postProyecto(proyecto: Proyecto): Observable<ProyectoResponse> {
    const req = proyecto;
    const res = this._httpClient.post<ProyectoResponse>(this._proyectosUrl + 'proyecto', req)
    return res
  }

  editProyecto(proyecto: Proyecto): Observable<ProyectoResponse> {
    const req = proyecto;
    //console.log("proyecto: ",proyecto)
    const res = this._httpClient.put<ProyectoResponse>(this._proyectosUrl+'proyecto/'+proyecto.email_gerente, proyecto)
    return res
  }

}