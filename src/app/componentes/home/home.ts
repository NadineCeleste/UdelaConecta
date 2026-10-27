import { Component, inject } from '@angular/core';
import { RouterModule, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Users } from '../../servicios/users';
import { Observable } from 'rxjs';
//import { AuthService } from '../../servicios/AuthService';
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
  activeTab: 'desarrolladores' | 'empresas' = 'desarrolladores';
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
    })
  ).subscribe();
}

  setActiveTab(tab: 'desarrolladores' | 'empresas'): void {
    this.activeTab = tab;
    this.openFaq = null;
  }

  scrollToTab(tab: 'desarrolladores' | 'empresas'): void {
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

  irAlSitioOficial(): void {
    window.open('https://www.udelaciudad.edu.ar/', '_blank');
  }

  irAContratos() {
  if (this.rolActual === 'gerente') {
    this.router.navigate(['/profile']);
  } else {
    alert('Esta sección es exclusiva para empresas. Registrate como empresa para acceder.');
  }
}
irAlPerfil(): void {
  if (this.rolActual === 'desarrollador') {
    this.router.navigate(['/profile']);
  } else {
    alert('Esta sección es exclusiva para desarrolladores. Registrate como desarrollador para acceder.');
  }
}

}