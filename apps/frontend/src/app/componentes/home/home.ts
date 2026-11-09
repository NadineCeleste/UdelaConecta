import { Component, inject } from '@angular/core';
import { RouterModule, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Users } from '../../servicios/users';
import { Observable } from 'rxjs';
import { AuthService, User } from '../../servicios/AuthService';
import { filter, tap } from 'rxjs/operators';
@Component({
  selector: 'app-home',
  imports: [RouterModule, CommonModule],
  templateUrl: './home.html',
  styleUrl: './home.css'
})

export class Home {



  user$: Observable<User | null>;
  loading = false;
  activeTab: 'estudiantes' | 'empresas' = 'estudiantes';
  openFaq: number | null = null;
  rolActual: string | null = null;

  perks = [
    { icon: 'attach_money', iconClass: 'g', title: '100% gratuito', desc: 'Publicar ofertas básicas no tiene costo.' },
    { icon: 'verified_user', iconClass: 'b', title: 'Perfiles verificados', desc: 'Todos los candidatos son alumnos de la Universidad de la Ciudad de Buenos Aires.' },
    { icon: 'bolt', iconClass: 'a', title: 'Respuesta rápida', desc: 'Recibís postulaciones en horas.' },
    { icon: 'school', iconClass: 'p', title: 'Formación técnica sólida', desc: 'Perfiles formados en desarrollo y análisis de sistemas.' },
    { icon: 'dashboard', iconClass: 't', title: 'Panel de gestión', desc: 'Administrá tus ofertas y postulantes fácilmente.' },
    { icon: 'favorite', iconClass: 'r', title: 'Impacto social', desc: 'Contribuís al desarrollo de jóvenes talentos.' },
  ];

  currentIndex = 0;

  prevSlide(): void {
    if (this.currentIndex > 0) {
      this.currentIndex--;
    }
  }

  nextSlide(): void {
    if (this.currentIndex < this.perks.length - 1) {
      this.currentIndex++;
    }
  }

  goToSlide(i: number): void {
    this.currentIndex = i;
  }

  /*    ngOnInit(): void {
       this.loadUser();
    } */


constructor(private authService: AuthService, private router: Router, private usersService: Users) {
  this.user$ = this.authService.user$;
}

ngOnInit(): void {
  this.usersService.userProfile$.pipe(
    filter(data => !!data),
    tap(data => {
      this.rolActual = data.rol || '';
      // Cada rol entra directo a su espacio: una empresa no aterriza en el
      // instructivo de estudiantes ni al revés. Sin rol conocido se mantiene
      // la pestaña de estudiantes y la barra de pestañas visible.
      if (this.rolActual) {
        this.activeTab = this.rolActual === 'estudiante' ? 'estudiantes' : 'empresas';
      }
    })
  ).subscribe();
}

  /** El rol se conoce recién cuando llega el perfil: hasta entonces no se pinta nada atado a él. */
  get esGerente(): boolean {
    return this.rolActual === 'gerente';
  }

  get esEstudiante(): boolean {
    return this.rolActual === 'estudiante';
  }

  /** Gerente e institución educativa comparten el espacio de empresas. */
  get esEmpresa(): boolean {
    return this.rolActual === 'gerente' || this.rolActual === 'institucion_educativa';
  }

  setActiveTab(tab: 'estudiantes' | 'empresas'): void {
    this.activeTab = tab;
    this.openFaq = null;
  }

  scrollToTab(tab: 'estudiantes' | 'empresas'): void {
    this.setActiveTab(tab);
    setTimeout(() => {
      const element = document.querySelector('.tabs-section');
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 100);
  }

  toggleFaq(index: number): void {
    this.openFaq = this.openFaq === index ? null : index;
  }

  /* Cada acción existe para un solo rol y la plantilla solo muestra la que
     corresponde: ya no hay alert() de "sección exclusiva". */
  irABuscarEmpleo(): void {
    this.router.navigate(['/contratos']);
  }

  irAPublicarOferta(): void {
    this.router.navigate(['/formcreatecontract']);
  }

  irAlPerfil(): void {
    this.router.navigate(['/profile']);
  }

}