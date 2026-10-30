import { Component, inject, Output, EventEmitter } from '@angular/core';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService, User } from '../../servicios/AuthService';
import { distinctUntilChanged, filter, Observable, tap } from 'rxjs';
import { Users } from '../../servicios/users';

interface BookPage {
  label?: string;
  title?: string;
  body?: string;
  bg: string;
  image?: string;
  isCover?: boolean;
  isBackCover?: boolean;
}

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './navbar.html',
  styleUrls: ['./navbar.css'],
})
export class Navbar {
  @Output() onLogin = new EventEmitter<void>();
  @Output() onRegister = new EventEmitter<void>();
  user$: Observable<User | null>;
  menuActive = false;
  isgests = false;
  private router = inject(Router);
  isOnContratos = false;
  private _subs: any;
  activeFragment?: string | null = null;

  /* ---- MINI LIBRO 3D ---- */
  showBookModal = false;
  bookSpread = 0;
  bookFlipState: 'idle' | 'forward' = 'idle';
  bookAnimating = false;
  bookSpreads = [[-1, 0], [1, 2], [3, 4], [5, 6], [7, -1]];
  bookPages: BookPage[] = [
    {
      isCover: true, title: '', body: 'UDELA CONECTA', bg: '#2a1b0e'
    },
    { label: 'Udela Conecta', title: '¿Qué es Udela Conecta?', body: 'Nuestro objetivo es acompañar a nuestros pares a dar sus primeros pasos dentro del mundo laboral IT.', bg: '#e8d4b9' },
    { label: 'Nosotros', title: '¿Quiénes Somos?', body: 'Detrás de Udela Conecta hay un grupo de estudiantes de la Universidad de la Ciudad de Buenos Aires que decidió transformar una problemática común en una solución real. ', bg: '#e8d4b9' },
    { label: 'Nuestra Universidad', title: 'Donde comenzó todo...', body: 'Todo el equipo está formado por estudiantes de la Universidad de la Ciudad de Buenos Aires.', bg: '#e8d4b9' },
    { label: 'Nuestra Misión', body: ' Creamos este espacio de apoyo donde el conocimiento compartido de las aulas se transforma en una herramienta real de inserción laboral', bg: '#e8d4b9' },
    { label: 'Para Empresas', body: 'Publicá tus ofertas y encontrá conectá con estudiantes y futuros profesionales IT preparados para incorporarse al mundo laboral', bg: '#e8d4b9' },
    { label: 'Talentos', title: 'Crecé con nosotros', body: 'Completá tu perfil profesional, compartí tus conocimientos y preparate para nuevas oportunidades en el sector IT.', bg: '#e8d4b9' },
    { isBackCover: true, title: '', body: '', bg: '#2a1b0e' }
  ];

  bookNext() {
    if (this.bookSpread >= this.bookSpreads.length - 1) return;
    this.bookSpread++;
  }

  bookPrev() {
    if (this.bookSpread <= 0) return;
    this.bookSpread--;
  }

  toggleBookModal() {
    this.showBookModal = !this.showBookModal;
    this.closeMenu();
  }

  closeBookModal() {
    this.showBookModal = false;
  }


  perfil: any = null;
  rolActual: string = '';

  isDropdownEstudianteOpen = false;
  isDropdownGerenteOpen = false;
  isModoOscuro = false;

  constructor(
    private authService: AuthService,
    private usersService: Users
  ) {

    this.user$ = this.authService.user$;
  }

  async ngOnInit(): Promise<void> {
    await this.inicializarDatos();

    this.isOnContratos = this.router.url?.startsWith('/contratos');

    // Inicializar tema
    const savedTheme = localStorage.getItem('theme');
    this.isModoOscuro = savedTheme === 'dark';
    this.updateThemeClass();

    this._subs = this.router.events.subscribe((ev: any) => {
      if (ev instanceof NavigationEnd) {
        this.isOnContratos = ev.urlAfterRedirects?.startsWith('/contratos');
        try {
          const parsed = this.router.parseUrl(ev.urlAfterRedirects || this.router.url);
          this.activeFragment = parsed.fragment ?? null;
        } catch (e) {
          this.activeFragment = null;
        }
      }
    });
  }

  async inicializarDatos() {
    this.usersService.userProfile$.pipe(

      filter(data => !!data),
      tap(data => {

        this.perfil = { ...data };
        this.rolActual = data.rol || '';
      })
    ).subscribe({
      error: (err) => {
        console.error('Error during data initialization:', err);
      }
    });

    // El flag de admin sale del backend, no de una lista de emails en el front
    this.authService.user$.subscribe({
      next: (user) => {
        this.isgests = !!user?.is_admin;
      },
      error: (err) => {
        console.error('Error during data initialization:', err);
      }
    })

    // Redirige al home justo después de loguearse
    this.user$.pipe(
      distinctUntilChanged(),
      filter(user => !!user) // cuando hay un usuario (recién logueado)
    ).subscribe(() => {
      const currentUrl = this.router.url;
      // Solo redirige si está en home o si la URL es la raíz
      if (currentUrl === '/' || currentUrl === '/home') {
        this.router.navigate(['/home']);
      }
    });
  }

  ngOnDestroy(): void {
    if (this._subs) { this._subs.unsubscribe?.(); }
  }
  toggleMenu() {
    this.menuActive = !this.menuActive;
  }

  closeMenu() {
    this.menuActive = false;
  }

  goBack() {
    window.history.back();
  }

  toggleDropdownEstudiante() {
    this.isDropdownEstudianteOpen = !this.isDropdownEstudianteOpen;
  }

  toggleDropdownGerente() {
    this.isDropdownGerenteOpen = !this.isDropdownGerenteOpen;
  }

  navigateToFragment(fragment: string) {
    this.router.navigate(['/contratos'], { fragment }).then(() => {
      this.activeFragment = fragment;
      this.closeMenu();

      setTimeout(() => {
        try {
          const el = document.getElementById(fragment);
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        } catch (err) {
          console.error('scroll error', err);
        }
      }, 120);
    });
  }

  navigateTo(path: string) {
    this.router.navigate([`/${path}`]);
    this.closeMenu();
  }

  async logout() {
    await this.authService.signOut();
    window.location.href = '/';
  }

  openBook() {
    this.toggleBookModal();
  }

  toggleModoOscuro() {
    this.isModoOscuro = !this.isModoOscuro;
    localStorage.setItem('theme', this.isModoOscuro ? 'dark' : 'light');
    this.updateThemeClass();
  }

  private updateThemeClass() {
    if (this.isModoOscuro) {
      document.body.classList.add('dark-theme');
    } else {
      document.body.classList.remove('dark-theme');
    }
  }
}
