import { Component, ViewEncapsulation } from '@angular/core';
import { Router, RouterModule, RouterOutlet } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Navbar } from './componentes/navbar/navbar';
import { Users } from './servicios/users';
import { distinctUntilChanged, filter, lastValueFrom, Observable, skip, Subscription, take, tap } from 'rxjs';
import { LoadingService } from './servicios/loading-service';
import { Spinner } from "./componentes/spinner/spinner";
import { AuthService, User } from './servicios/AuthService';
import { FormsModule } from '@angular/forms';
import { Usuario } from './models/users/usuario';
import { Alertas } from './componentes/alertas/alertas';
import { AlertService } from './servicios/alertService';
import { Chatbot } from './componentes/chatbot/chatbot';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    Navbar,
    RouterOutlet,
    RouterModule,
    CommonModule,
    Spinner,
    FormsModule,
    Alertas,
    Chatbot
  ],
  templateUrl: './app.html',
  styleUrls: ['./app.css'],
  encapsulation: ViewEncapsulation.None
})
export class App {
  isModoOscuro: boolean = false;
  private canvas?: HTMLCanvasElement;

  user$: Observable<User | null>;
  userEmail: string | null = null;
  private authSub?: Subscription;
  selectedRole: string = '';
  usuarioRol: string = '';

  login_email = '';
  login_password = '';
  signup_email = '';
  signup_password = '';
  loading = false;
  confirmationSent = false;
  showLoginModal = false;
  showRegisterModal = false;
  showForgotPasswordModal = false;
  reset_email = '';
  resetSent = false;
  title = 'udelaConecta';

  searchKeyword = '';
  searchLocation = '';

  handleSearch(tag?: string) {
    if (tag) {
      this.searchKeyword = tag;
    }
    if (!this.userEmail) {
      this.toggleLoginModal();
    } else {
      this.router.navigate(['/contratos']);
    }
  }

  cargandoData = true;

  constructor(
    /* private _loaderService: LoadingService, */
    protected usersService: Users,
    private router: Router,
    private authService: AuthService,
    private alertService: AlertService
  ) {

    this.user$ = this.authService.user$;
  }



  get esSoloPerfil(): boolean {
    return this.router.url.startsWith('/profile/');
  }

  async ngOnInit() {

    //this.userEmail = this.authService.getCurrentUser()?.email || '';

    // Pausamos la ejecucion hasta que Supabase lea la sesion del navegador
    await this.authService.session;
    this.checkInitialTheme();
    await this.inicializarDatos();
  }

  checkInitialTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
      this.isModoOscuro = true;
      document.body.classList.add('dark-theme');
    }
  }

  toggleModoOscuro() {
    this.isModoOscuro = !this.isModoOscuro;
    if (this.isModoOscuro) {
      document.body.classList.add('dark-theme');
      localStorage.setItem('theme', 'dark');
    } else {
      document.body.classList.remove('dark-theme');
      localStorage.setItem('theme', 'light');
    }
  }

  async inicializarDatos() {
    //this.cargandoData = true;

    // Evita suscripciones duplicadas cuando se vuelve a llamar tras crear el usuario (B-07)
    this.authSub?.unsubscribe();
    this.authSub = this.authService.userEmail$.pipe(

      distinctUntilChanged()
      //,filter(email => email !== null)

    ).subscribe(async email => {
      this.cargandoData = true;
      this.userEmail = email;
      if (email) {
        const usuarioExistente: any = await this.checkUserExists(email);
        if (usuarioExistente.error) {
          // Un error del servidor no significa "usuario inexistente" (E-10)
          this.alertService.error('No se pudo conectar con el servidor para verificar tu perfil');
        } else if (usuarioExistente.data.existe == 1) {

          this.usuarioRol = usuarioExistente.data.tabla
          this.closeModals(); //acá lo pusimos en la call moni celes ariel

          // debug --> console.log("Usuario hallado en BBDD: ", this.usuarioRol)


          try {
            const usuarioHalladoEnBBDD = await this.getUser(email, usuarioExistente.data.tabla)

            this.usersService.setUserProfile({
              ...usuarioHalladoEnBBDD,
              email: email,
              rol: usuarioExistente.data.tabla
            })
          } catch {
            // Sin esto la promesa rechazada dejaba el spinner girando para siempre
            this.alertService.error('No se pudo cargar tu perfil');
          }
        } else {
          this.usuarioRol = '';
          console.log("Usuario no hallado, mostrando selector de rol")
        }
      } else {
        //para cuando no hay sesión activa
        this.usuarioRol = '';
      }
      this.cargandoData = false;
    });
  }

  async checkUserExists(email: string) {
    try {
      const res = await lastValueFrom(this.usersService.checkUserExists(email));
      return res
    } catch (error) {
      console.error('Error checkeando existencia de usuario:', error);
      return { data: { existe: 0, tabla: null }, error: true };
    }
  }

  async getUser(email: string, table: string) {

    try {

      const res = await lastValueFrom(this.usersService.getUsuarioByEmailAndTable(email, table));
      return res.data
    } catch (error) {
      console.error('Error obteniendo usuarios:', error);
      throw error;
    }
  }


  async handleLogin(event: Event) {
    event.preventDefault();
    this.loading = true;
    this.cargandoData = true;

    try {

      const { data, error } = await this.authService.signIn(this.login_email, this.login_password);
      if (error) throw error;

    } catch (error: any) {
      this.cargandoData = false;
      this.alertService.error(error.error_description || error.message);
    } finally {
      this.loading = false;
    }
    
  }

  async handleSignUp(event: Event) {
    event.preventDefault();
    this.loading = true;
    this.cargandoData = true;

    try {
      const { data, error } = await this.authService.signUp(this.signup_email, this.signup_password);

      if (error) throw error;

      if (data.user && !data.session) {
        this.confirmationSent = true;
        
      }

      this.alertService.success("Sesión iniciada correctamente");
      
    } catch (error: any) {
      this.alertService.error(error.message || 'Hubo problemas al crear tu cuenta');

    } finally {
      this.loading = false;
    }
    this.cargandoData = false;
  }

  async handleCreateUser() {
    if (!this.selectedRole) {
      this.alertService.warning('Por favor selecciona un rol');
      return;
    }
    this.cargandoData = true;

    try {
      this.loading = true;
      await lastValueFrom(this.usersService.createUserByRole(this.userEmail!, this.selectedRole));

      console.log('Usuario creado con éxito');

      await this.inicializarDatos();

    } catch (error) {
      console.error('Error al crear:', error);
      this.alertService.error('No se pudo crear el perfil');
    } finally {
      this.loading = false;
    }
    this.cargandoData = false;
  }

  async logout() {
    this.cargandoData = true;
    try {

      await this.authService.signOut();


      this.userEmail = null;
      this.usuarioRol = '';
      this.selectedRole = '';


      await this.router.navigate(['/']);

      console.log("Sesión cerrada correctamente");
      this.alertService.success("Sesión cerrada correctamente");
    } catch (error) {
      console.error("Error al cerrar sesión:", error);
      this.alertService.error("Error al cerrar sesión: " + error);
    } finally {
      this.cargandoData = false;
    }
  }

  scrollTo(id: string) {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  toggleLoginModal() {
    this.showLoginModal = !this.showLoginModal;
    this.showRegisterModal = false;
    this.showForgotPasswordModal = false;
  }

  toggleRegisterModal() {
    this.showRegisterModal = !this.showRegisterModal;
    this.showLoginModal = false;
  }

  closeModals() {
    this.showLoginModal = false;
    this.showRegisterModal = false;
    this.showForgotPasswordModal = false;
    this.confirmationSent = false;
    this.resetSent = false;
  }

  toggleForgotPasswordModal() {
    this.showForgotPasswordModal = !this.showForgotPasswordModal;
    this.showLoginModal = false;
    this.showRegisterModal = false;
    this.resetSent = false;
  }

  async handleResetPassword(event: Event) {
    event.preventDefault();
    this.loading = true;
    try {
      const { error } = await this.authService.resetPassword(this.reset_email);
      if (error) throw error;
      this.resetSent = true;
    } catch (error: any) {
      this.alertService.error(error.message || 'Error al enviar el correo de recuperación');
    } finally {
      this.loading = false;
    }
  }

  //login social handle
  async handleSocialLogin(provider: 'google') {
    this.loading = true;
    this.cargandoData = true;
    try {
      const { data, error } = await this.authService.signInWithSocial(provider);
      if (error) throw error;
      // Supabase redirigirá al proveedor, luego del auth vuelve a la app al .com.ar
    } catch (error: any) {
      this.cargandoData = false;
      this.alertService.error(error.message || 'Error en el inicio de sesión');
    } finally {
      this.loading = false;
    }
  }

} 
