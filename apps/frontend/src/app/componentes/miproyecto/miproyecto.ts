import { Component, inject } from '@angular/core';
import { Users } from '../../servicios/users';
import { ProyectoService } from '../../servicios/miproyecto';
import { Proyecto } from '../../models/proyectos';
import { RouterModule } from '@angular/router';
import { LoadingService } from '../../servicios/loading-service';
import { Observable } from 'rxjs';
import { AuthService, User } from '../../servicios/AuthService';



@Component({
  selector: 'app-miproyecto',
  imports: [RouterModule],
  templateUrl: './miproyecto.html',
  styleUrl: './miproyecto.css',
})
export class Miproyecto {

  user$: Observable<User | null>;
  perfil: any = null;
  rolActual: string = ''

  constructor(
    private _apiService: ProyectoService,
    private _loaderService: LoadingService,

    private authService: AuthService,
    private usersService: Users
  ) {
    // Assign the observable from the service
    this.user$ = this.authService.user$;
  }
  /* private _usersService = inject(Users); */
  /* user: any; */
  proyecto?: Proyecto;

  async ngOnInit(): Promise<void> {

    // Suscripción para tener la data siempre actualizada
    this.usersService.userProfile$.subscribe(data => {
      if (data) {
        this.perfil = { ...data }; // Copia para editar sin afectar el estado global antes de tiempo
        // Determina el rol (esto lo saca de la tabla que devolvió la API en app.ts)
        this.rolActual = data.rol || '';
        // Se pide el proyecto recién cuando hay perfil cargado (B-03)
        if (this.perfil.email) {
          this.mostrarProyecto(this.perfil.email);
        }
      }

    });

  }




  mostrarProyecto(email: string) {
    this._loaderService.showLoader()
    this._apiService.getProyectoPorEmail(email).subscribe({
      next: (res) => {
        //console.log(`${res.count} ${res.message}`)
        this.proyecto = res.data[0];
      },
      error: (error: string) => {
        console.log('desde el componente error ' + error)
      },
      complete: () => {
        this._loaderService.hideLoader();
      }
    });
  }

}