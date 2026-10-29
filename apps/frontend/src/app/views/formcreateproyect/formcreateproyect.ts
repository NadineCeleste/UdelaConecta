import { Component, inject } from '@angular/core';
import { FormsModule, NgForm } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Proyecto } from '../../models/proyectos';
import { Users } from '../../servicios/users';
import { ProyectoService } from '../../servicios/miproyecto';
import { ActivatedRoute, Router } from '@angular/router';
import { filter, Observable, of, switchMap } from 'rxjs';
import { AuthService, User } from '../../servicios/AuthService';
import { AlertService } from '../../servicios/alertService';


@Component({
  selector: 'app-formcreateproyect',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './formcreateproyect.html',
  styleUrl: './formcreateproyect.css',
})
export class Formcreateproyect {


  user$: Observable<User | null>;
  perfil: any = null;
  rolActual: string = ''

  espost = false;
  esedit = true;
  formularioEnviado = false;
  proyecto: Proyecto = {
    nombre: '',
    description: '',
    info_link: '',
    buscando_devs: true,//siempre arranca true
    email_gerente: ''
  }

  constructor(
    private _apiService: ProyectoService,
    private router: Router,
    private route: ActivatedRoute,

    private authService: AuthService,
    private usersService: Users,
    private alertService: AlertService
  ) {
    // Assign the observable from the service
    this.user$ = this.authService.user$;
  }

  async ngOnInit(): Promise<void> {

    await this.inicializarDatos();

  }

async inicializarDatos() {

  // la lógica de esta función es que primero busca la data de usuario (userservice) a la que está suscripto
  // luego carga eso en variables locales
  // DESPUÉS de eso, busca en los proyectos si hay algun proyecto relacionado con el email del rol asignado en local
  // si hay, se entra en modo editar. sino, en modo post / crear.

  this.usersService.userProfile$.pipe(
    // 1. Wait for valid profile data
    filter(data => !!data),
    switchMap(data => {
      // Store profile immediately
      this.perfil = { ...data };
      this.rolActual = data.rol || '';

      if (data.email) {
        // 2. Call the API
        return this._apiService.getProyectoPorEmail(data.email);
      } else {
        // No email found? Pass null to the next step
        return of(null);
      }
    })
  ).subscribe({
    next: (res) => {
      
      if (res && res.data && res.data.length > 0) {
        this.proyecto = res.data[0];
        this.esedit = true;
        this.espost = false;
        console.log("Proyecto encontrado: Editing mode active.");
      } else {
        // importante: si todo falla, igual hay que cargarle al proyecto un email
        // porque la API está esperando ese dato en el método POST.
        this.proyecto.email_gerente = this.perfil.email;
        this.espost = true;
        this.esedit = false;
        console.log("Proyecto no encontrado: Modo creación.");
      }
    },
    error: (err) => {
      console.error('Error during data initialization:', err);
      // Fallback to post mode on error to avoid breaking the UI
      this.espost = true;
      this.esedit = false;
    }
  });
}

  enviar(form: NgForm) {
    if (form.invalid) {
      return;
    }

    const dataParaEnviar = {
      ...this.proyecto,
    };

    this._apiService.postProyecto(this.proyecto).subscribe({
      next: (res) => {
        console.log(res.message)
        this.router.navigate(['/miproyecto']);
        this.alertService.success('Proyecto creado con éxito');
      },
      error: (error: string) => {
        console.log(error)
        this.alertService.error('Error al crear el proyecto');
      }
    });

  }

  editar(form: NgForm) {
    if (form.invalid) {
      return;
    }

    const dataParaEnviar = {
      ...this.proyecto,
    };

    this._apiService.editProyecto(this.proyecto).subscribe({
      next: (res) => {
        console.log(res.message)
        this.router.navigate(['/miproyecto']);
        this.alertService.success('Proyecto actualizado con éxito');
      },
      error: (error: string) => {
        console.log(error)
        this.alertService.error('Error al actualizar el proyecto');
      }
    });

  }

}