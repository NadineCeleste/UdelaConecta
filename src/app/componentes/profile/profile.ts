import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { Users } from './../../servicios/users';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { lastValueFrom } from 'rxjs';
import { CommonModule } from '@angular/common';
import { ProyectoService } from '../../servicios/miproyecto';
import { ContratoService } from '../../servicios/contrato';
import { Contrato } from '../../models/contrato';
import { AlertService } from '../../servicios/alertService';
import { PortfolioComponent } from '../portfolio-component/portfolio-component';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, FormsModule, RouterModule, PortfolioComponent],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.css'
})
export class ProfileComponent implements OnInit {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private usersService = inject(Users);
  private projectService = inject(ProyectoService)


  perfil: any = null;
  rolActual: string = '';
  isEditing: boolean = false;
  loading: boolean = false;
  maxDate: string = '';
  minDate: string = '';

  // --- VARIABLES PARA ARCHIVOS ---
  archivoCV: File | null = null;            // Para el Currículum
  archivoSeleccionado: File | null = null; // Para el Portfolio

  // --- VARIABLES PARA HABILIDADES ---
  mostrandoFormulario: boolean = false;
  nuevaHabilidad = {
    nombre: '',
    nivel: 'principiante'
  };

  // --- IDIOMAS ---
  mostrandoFormIdioma: boolean = false;
  nuevoIdioma = {
    nombre: '',
    nivel: 'A1 - Principiante'
  };

  // CONTROL DE NAVEGACIÓN
  seccionActiva: string = 'info';
  isSidebarOpen: boolean = false;

  //ofertas/contratos del gerente/empresa
  ofertas: Contrato[] = []; // las ofertas activas
  private contratoService = inject(ContratoService); // inyeccion servicio contrato
  private alertService = inject(AlertService); // inyeccion servicio alertas

  isOwnProfile = true; // para saber si es el perfil gerente o desarrollador


  async ngOnInit() {
    //obtener email de la url si viniera

    this.calcularLimitesFechas();

    const emailDesdeUrl = this.route.snapshot.paramMap.get('email');

    this.usersService.userProfile$.subscribe(async data => {
      if (!data) return;

      const miEmail = data.email;

      //si hay un email en la URL y NO es el mío(gerente), cargo el perfil de esa persona, deberia ser un desarollador
      if (emailDesdeUrl && emailDesdeUrl !== miEmail) {
        this.isOwnProfile = false;

        // Buscar en qué tabla está ese usuario (desarrollador o gerente)
        const existe = await lastValueFrom(this.usersService.checkUserExists(emailDesdeUrl));

        if (existe.data.existe === 1) {
          const tabla = existe.data.tabla; // 'desarrollador', 'gerente', etc.

          // Traer los datos de esa tabla
          const perfilAjeno = await lastValueFrom(
            this.usersService.getUsuarioByEmailAndTable(emailDesdeUrl, tabla)
          );

          // Armar el perfil para mostrarlo
          this.perfil = {
            ...perfilAjeno.data,
            email: emailDesdeUrl,
            rol: tabla,
            // Mapear habilidades e idiomas (igual que haces abajo)
            habilidades: (perfilAjeno.data.habilidades || []).map((h: any) => ({
              nombre: h.nombre_habilidad,
              nivel: h.nivel_habilidad
            })),
            idiomas: (perfilAjeno.data.idiomas || []).map((i: any) => ({
              nombre: i.nombre_idioma,
              nivel: i.nivel_idioma
            })),
            posicion: perfilAjeno.data.puesto_actual
          };
          this.rolActual = tabla;
        } else {
          this.alertService.error('Usuario no encontrado');
          this.router.navigate(['/']);
        }

      } else {
        this.perfil = {
          ...data,
          //habilidades: data.habilidades || [],
          //idiomas: data.idiomas || [],
          /* empresa_nombre: data.empresa_nombre || '', esto sale de otro servicio, proyecto */
          /* web_empresa: data.web_empresa || '', */
          /* descripcion_empresa: data.descripcion_empresa || '', */
          /* ubicacion_empresa: data.ubicacion_empresa || '', */
          telefono: data.telefono,
          posicion: data.puesto_actual,
          habilidades: (data.habilidades || []).map((h: any) => ({
            nombre: h.nombre_habilidad,   // back → front
            nivel: h.nivel_habilidad
          })),
          idiomas: (data.idiomas || []).map((i: any) => ({
            nombre: i.nombre_idioma,
            nivel: i.nivel_idioma
          })),

        };
        this.rolActual = data.rol || '';

        this.projectService.getProyectoPorEmail(data.email).subscribe({
          next: (res) => {
            //console.log(`${res.count} ${res.message}`)
            //console.log(res.data[0])
            this.perfil.proyecto = res.data[0];

          },
          error: (error: string) => {
            console.log('desde el componente perfil error ' + error)
            this.alertService.error("Error al cargar el perfil, " + error);
          }
        });
      }
      const tabParam = this.route.snapshot.queryParamMap.get('tab');
      if (tabParam) {
        this.seccionActiva = tabParam;
        if (tabParam === 'ofertas') {
          this.cargarOfertas();
        }
      }
    });
  }
  //El metodo "calularLimiteFechas()" esta oara ni poner datos por fuera de los parametros de edad.
  calcularLimitesFechas() {
  const hoy = new Date();

  // Fecha máxima: Hoy menos 18 años
  const fechaMax = new Date(hoy.getFullYear() - 18, hoy.getMonth(), hoy.getDate());
  this.maxDate = fechaMax.toISOString().split('T')[0];

  // Fecha mínima: Hoy menos 100 años (límite razonable de edad)
  const fechaMin = new Date(hoy.getFullYear() - 100, hoy.getMonth(), hoy.getDate());
  this.minDate = fechaMin.toISOString().split('T')[0];
}

  // --- MÉTODOS PARA ARCHIVOS ---

  // Para el Currículum 
  onCVSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.archivoCV = file;
    }
  }
  // Bloque los numeros dentro de los campos NOMBRE y APELLIDO. 
  permitirSoloLetras(event: KeyboardEvent): boolean {
  const regex = new RegExp("^[a-zA-ZñÑáéíóúÁÉÍÓÚ\\s]+$");
  const tecla = event.key;

  if (!regex.test(tecla)) {
    event.preventDefault(); // Bloquea la escritura de la tecla
    return false;
  }
  return true;

  
  
  
}

  // Para el Portfolio 
  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.archivoSeleccionado = file;
    }
  }

  // Función de borrar 
  borrarArchivo(tipo: string) {
    if (tipo === 'cv') {
      this.archivoCV = null;
    } else {
      this.archivoSeleccionado = null;
    }
  }

  // --- HABILIDADES ---
  eliminarHabilidad(indice: number) {
    this.perfil.habilidades.splice(indice, 1);
  }

  guardarHabilidad() {
    this.loading = true;
  const nombreNuevo = this.nuevaHabilidad.nombre.trim().toLowerCase();

  if (!nombreNuevo) return;

  const duplicado = this.perfil.habilidades.some(
    (h: any) => h.nombre.toLowerCase() === nombreNuevo
  );

  if (duplicado) {
    this.alertService.error('Esta habilidad ya fue agregada.');
    this.loading = false;
    return;
  }

  this.perfil.habilidades.push({ ...this.nuevaHabilidad });
  this.nuevaHabilidad = { nombre: '', nivel: 'principiante' };
  this.mostrandoFormulario = false;
  this.loading = false;
}


  // --- IDIOMAS ---
  guardarIdioma() { 
  this.loading = true;
  const nombreNuevo = this.nuevoIdioma.nombre.trim().toLowerCase();

  if (!nombreNuevo) return;

  const duplicado = this.perfil.idiomas.some(
    (i: any) => i.nombre.toLowerCase() === nombreNuevo
  );

  if (duplicado) {
    this.alertService.error('Este idioma ya fue agregado.');
    this.loading = false;
    return;
  }

  this.perfil.idiomas.push({ ...this.nuevoIdioma });
  this.nuevoIdioma = { nombre: '', nivel: 'A1 - Principiante' };
  this.mostrandoFormIdioma = false;
  this.loading = false;
}

  // --- NAVEGACIÓN Y EDICIÓN ---
  cambiarSeccion(seccion: string) {
    this.seccionActiva = seccion;
    this.isEditing = false;
    this.mostrandoFormulario = false;
    this.mostrandoFormIdioma = false;

    if (seccion === 'ofertas') {
      this.cargarOfertas();
    }
  }

  toggleEdit() {
    this.isEditing = !this.isEditing;
    if (!this.isEditing) {
      this.mostrandoFormulario = false;
      this.mostrandoFormIdioma = false;
    }
  }

  toggleSidebar() {
    this.isSidebarOpen = !this.isSidebarOpen;
  }

  soloNumeros(event: KeyboardEvent) {
    const charCode = event.which ? event.which : event.keyCode;
    if (charCode > 31 && (charCode < 48 || charCode > 57)) {
      event.preventDefault();
    }
  }

  async handleUpdate() {
    if (!this.rolActual) return this.alertService.error("No se detectó el rol del usuario");


    if (this.rolActual == 'desarrollador') {
      //como en db posicion es puesto_actual lo voy a renombrar antes de enviar
      //las tablas y habilidades idioma son nombre_habilidad, nivel_habilidad, nombre_idioma, nivel_idiona
      const userDevPayload = {
        ...this.perfil,
        puesto_actual: this.perfil.posicion,
        //  HABILIDADES → formato back
        habilidades: (this.perfil.habilidades || [])
          .filter((h: any) => h && h.nombre) // saca null/undefined/vacío
          .map((h: any) => ({
            nombre_habilidad: String(h.nombre || '').trim(),
            nivel_habilidad: h.nivel || 'principiante'
          })),
        //  IDIOMAS → formato back
        idiomas: (this.perfil.idiomas || [])
          .filter((i: any) => i && i.nombre)
          .map((i: any) => ({
            nombre_idioma: String(i.nombre || '').trim(),
            nivel_idioma: i.nivel || 'A1 - Principiante'
          }))

      };

      //console.log('PAYLOAD QUE SALE', JSON.stringify(userDevPayload, null, 2));

      try {
        this.loading = true;
        const email = this.perfil.email;
        await lastValueFrom(this.usersService.updateUserByRole(this.rolActual, email, userDevPayload));
        this.isEditing = false;
        this.alertService.success('Perfil actualizado con éxito');
      } catch (error) {
        console.error('Error en PUT:', error);
        this.alertService.error('Hubo un error al guardar los cambios');
      } finally {
        this.loading = false;
      }
    }

    if (this.rolActual == 'gerente') {
      try {
        this.loading = true;
        const email = this.perfil.email;
        await lastValueFrom(this.projectService.editProyecto(this.perfil.proyecto)) && lastValueFrom(this.usersService.updateUserByRole(this.rolActual, email, this.perfil));
        this.isEditing = false;
        this.alertService.success('Perfil actualizado con éxito');
      } catch (error) {
        console.error('Error en PUT:', error);
        this.alertService.error('Hubo un error al guardar los cambios');
      } finally {
        this.loading = false;
      }
    }


  }

  //obtener ofertas para el perfil tipo gerente empresa
  cargarOfertas() {
    if (!this.perfil?.email || this.rolActual !== 'gerente') return;
    this.contratoService.getContratosByEmailGerente(this.perfil.email).subscribe({
      next: (res) => {
        const rawOfertas = res.data || [];
        this.ofertas = rawOfertas.map((oferta: any) => {
          let seniorityParsed: string[] = [];
          if (Array.isArray(oferta.seniority_deseado)) {
            seniorityParsed = oferta.seniority_deseado;
          } else if (typeof oferta.seniority_deseado === 'string') {
            const trimmed = oferta.seniority_deseado.trim();
            if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
              try {
                seniorityParsed = JSON.parse(trimmed);
              } catch (e) {
                seniorityParsed = [trimmed];
              }
            } else if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
              const cleaned = trimmed.slice(1, -1).replace(/"/g, '');
              seniorityParsed = cleaned ? cleaned.split(',') : [];
            } else {
              seniorityParsed = trimmed ? [trimmed] : [];
            }
          }
          return {
            ...oferta,
            seniority_deseado: seniorityParsed
          };
        });
      },
      error: (err) => console.error('Error al obtener ofertas', err)
    });
  }

  formatearFecha(fechaStr?: string): string {
    if (!fechaStr) {
      fechaStr = new Date().toISOString().split('T')[0];
    }
    try {
      const fecha = new Date(fechaStr);
      if (isNaN(fecha.getTime())) {
        return fechaStr;
      }
      const opciones: Intl.DateTimeFormatOptions = { day: '2-digit', month: 'short', year: 'numeric' };

      return fecha.toLocaleDateString('es-ES', opciones).replace(/de /g, '').trim();
    } catch (e) {
      return fechaStr;
    }
  }

  //eliminar oferta/contrato //no existe en contrato service delete por ahora
  async eliminarOferta(contrato: Contrato) {
    if (!contrato.id) return;
    const confirmado = await this.alertService.confirm(
      '¿Estás seguro de eliminar esta oferta?',
      'Eliminar oferta'
    );

    if (!confirmado) return;

    this.contratoService.deleteContrato(contrato.id.toString()).subscribe({
      next: () => {
        this.ofertas = this.ofertas.filter(o => o.id !== contrato.id);
      },
      error: (err) => console.error('Error al eliminar', err)
    });
  }

   eliminarIdioma(indice: number) {
    this.perfil.idiomas.splice(indice, 1);
  }

  formatLanguageLevel(nivel: string): string {
    return nivel || 'Básico';
  }

  get isProfileEmpty(): boolean {
    if (!this.perfil) return true;
    return !this.perfil.nombre || this.perfil.nombre === '';
  }


}