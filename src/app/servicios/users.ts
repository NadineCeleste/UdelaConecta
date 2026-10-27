import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { catchError, of, Observable, BehaviorSubject, tap } from 'rxjs';
import { environment } from '../environments/environment';


@Injectable({
  providedIn: 'root'
})
export class Users {

  private USERSURL = environment.apiUrl;

  // Este es el "almacen" privado y el observable público que observarán los componentes
  private userProfileSubject = new BehaviorSubject<any>(null);
  public userProfile$ = this.userProfileSubject.asObservable();

  constructor(private _httpClient: HttpClient) { }

  // ########### MÉTODOS DE MANEJO DE SESIÓN ###########

  // Método que llama a la API para consultar si hay algún usuario en alguna de las tres tablas de usuarios con determinado email
  checkUserExists(email: string): Observable<any> {
    const url = `${this.USERSURL}usuario/${email}`;

    return this._httpClient.get<any>(url).pipe(
      catchError((error) => {
        // Si el servidor responde 404, devolvemos el objeto "no existe" manualmente
        // Esto lo tuve que poner porque configuramos la API para que responda con ERROR 404 si no hay usuarios con el mail.
        // pero no es un "error" propiamente dicho, es un resultado esperable: aún no se creó ese usuario. Entonces manualmente
        // seteamos que devuelva data manejable (data y menssage)
        if (error.status === 404) {
          return of({
            data: { existe: 0, tabla: null },
            message: "El usuario no existe en la DB"
          });
        }
        // Si es otro error (500, sin internet, etc), lo lanzamos de verdad
        throw error;
      })
    );

  }

  // Método para actualizar el perfil desde cualquier lugar
  setUserProfile(data: any) {
    this.userProfileSubject.next(data);
  }

  // Método para obtener el valor actual sin observables (opcional)
  getUserProfileValue() {
    return this.userProfileSubject.value;
  }

  // Este es el método que realmente devuelve toda la data del usuario, para eso hay que saber la tabla en la que se encuentra (ver checkUserExists())
  getUsuarioByEmailAndTable(email: string, table: string): Observable<any> {
    const url = this.USERSURL + `usuario/${email}/${table}`
    const res = this._httpClient.get<any>(url);
    return res;
  }


  createUserByRole(email: string, role: string): Observable<any> {
    // role vendrá como 'desarrollador', 'gerente' o 'institucion'
    const url = `${this.USERSURL}${role}`;
    const body = { email: email };

    return this._httpClient.post<any>(url, body);
  }

  updateUserByRole(role: string, email: string, userData: any): Observable<any> {
    // 1.a) Mapea roles a endpoints
    const roleEndpoints: { [key: string]: string } = {
      'desarrollador': 'desarrollador',
      'gerente': 'gerente',
      'institucion_educativa': 'institucion_educativa'
    };

    const segment = roleEndpoints[role];

    // Validación de seguridad
    if (!segment || !email) {
      console.error("Faltan datos críticos: Rol:", role, "Email:", email);
      throw new Error("No se puede actualizar sin rol o email");
    }

    if (!segment) {
      console.error("ERROR: No se reconoce el rol:", role);
      throw new Error("Rol no válido para actualización");
    }

    const url = `${this.USERSURL}usuario/${email}`;
    //console.log("URL: ", url)
    //console.log("data: ", userData)
    return this._httpClient.put<any>(url, userData).pipe(
      tap(() => {
        // Actualiza el estado local para que los cambios se vean al instante
        /* const current = this.getUserProfileValue(); */
        const current = this.userProfileSubject.value;
        this.setUserProfile({ ...current, ...userData });
      })
    );
  }


  // ########### OTROS MÉTODOS ###########

  // Trae todos los desarrolladores
  getAllDesarrolladores(): Observable<any> {
    const url = this.USERSURL;
    const desarrolladores = this._httpClient.get<any>(url + "desarrolladores");
    return desarrolladores
  }






}