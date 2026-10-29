import { Component, Input } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ContratoCard } from '../../models/cards/contrato-card';
import { CommonModule, ViewportScroller } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Contrato } from '../../models/contrato';
import { RouterModule } from '@angular/router';
import { ContratoDetail } from '../contrato-detail/contrato-detail';
import { ContratoService } from '../../servicios/contrato';
import { Users } from '../../servicios/users';
import { LoadingService } from '../../servicios/loading-service';

@Component({
    selector: 'app-contratos',
    imports: [
        CommonModule,
        RouterModule,
        FormsModule,
        ContratoDetail],
    templateUrl: './contratos.html',
    styleUrl: './contratos.css'
})

export class Contratos {

    usuarioLogueado: any;
    perfil: any = null;
    rolActual: string = '';
    loading: boolean = false;

    todosLosContratos: Contrato[] = [];
    contratosCards: ContratoCard[] = [];
    contratosDisponibles: Contrato[] = [];
    contratosDisponiblesCopia: Contrato[] = [];//para recuperar despues de filtrar
    contratosAsignados: Contrato[] = [];
    contratosPendientes: Contrato[] = [];
    verContratosNoPostulados: boolean = false;

    mostrandoContratoDetail = false;
    contratoAMostrarDetail: Contrato | undefined;
    pendingSelectContratoId: number | undefined;

    busqueda: string = '';
    filtroModalidad: string = '';
    filtroSeniority: string = '';
    drawerAbierto: boolean = false;

    pendingFragment?: string | undefined;

    constructor(
        private _apiService: ContratoService,
        private viewportScroller: ViewportScroller,
        private _usersService: Users,
        private _loaderService: LoadingService,
        private route: ActivatedRoute,

        private usersService: Users
    ) { }




    ngOnInit() {
        this.route.queryParams.subscribe(params => {
            if (params['id']) {
                const id = Number(params['id']);
                if (!isNaN(id)) {
                    this.pendingSelectContratoId = id;
                }
            }
        });

        // Suscripción para tener la data siempre actualizada.
        // Esperamos a tener perfil cargado antes de pedir los contratos,
        // porque sino this.perfil.email es null y el filtro de postulaciones falla.
        let lastEmail: string | undefined;
        let lastRol: string | undefined;
        this.usersService.userProfile$.subscribe(data => {
            if (!data) return;
            this.perfil = { ...data };
            this.rolActual = data.rol || '';

            // Solo refrescamos si cambió algo relevante para evitar loops
            if (data.email !== lastEmail || this.rolActual !== lastRol) {
                lastEmail = data.email;
                lastRol = this.rolActual;
                this.mostrarTodosLosContratos();
            }
        });
    }



    mostrarTodosLosContratos() {
        // Sin perfil cargado no podemos clasificar postulaciones, esperamos.
        if (!this.perfil || !this.perfil.email) {
            return;
        }

        this._loaderService.showLoader()

        //esto va a guardar el observable  al que nos vamos a suscribir
        let data;
        if (this.rolActual === 'estudiante') {
            data = this._apiService.getContratosLibres();
        } else {
            data = this._apiService.getContratosByEmailGerente(this.perfil.email);

        }

        data.subscribe({
            next: (res) => {
                // Normalizamos campos que el backend a veces devuelve como string
                // separado por comas en vez de array (rompe los .join / .includes).
                this.todosLosContratos = (res.data || []).map(c => ({
                    ...c,
                    seniority_deseado: this.toArray(c.seniority_deseado),
                    postulaciones: this.toArray(c.postulaciones as any),
                }));
                this.createCards(this.todosLosContratos)

                if (this.pendingFragment) {

                    setTimeout(() => this.scrollToSection(this.pendingFragment!), 50);
                    this.pendingFragment = undefined;
                }
            },
            error: (error: string) => {
                console.log('desde el componente contratos error ' + error)
            },
            complete: () => {
                this._loaderService.hideLoader();
            }
        });

    }

    filtrarContratos(): void {
        const term = this.busqueda.toLowerCase().trim();
        let filtrados = [...this.todosLosContratos];

        if (term) {
            filtrados = filtrados.filter(c =>
                c.titulo?.toLowerCase().includes(term)
            );
        }

        if (this.filtroModalidad) {
            filtrados = filtrados.filter(c =>
                c.modalidad?.toLowerCase() === this.filtroModalidad.toLowerCase()
            );
        }

        if (this.filtroSeniority) {
            const sel = this.filtroSeniority.toLowerCase();
            filtrados = filtrados.filter(c =>
                (c.seniority_deseado || []).some(s => String(s).toLowerCase().includes(sel))
            );
        }

        this.createCards(filtrados);
    }

    limpiarFiltros(): void {
        this.filtroModalidad = '';
        this.filtroSeniority = '';
        this.filtrarContratos();
    }

    toggleContratosDisponiblesNoPostulados(): void {
        this.verContratosNoPostulados = !this.verContratosNoPostulados;

        if (this.verContratosNoPostulados) {

            this.contratosDisponibles = this.contratosDisponiblesCopia.filter(
                c => !c.postulaciones?.includes(this.perfil.email)
            );

        } else {

            this.contratosDisponibles = [...this.contratosDisponiblesCopia];
        }

        //this.createCards(contratosFiltrados);
    }

    createCards = (contratos: Contrato[]): void => {
        // separar contratos en disponibles (no ocupados), pendientes (postulaciones del usuario) y asignados
        this.contratosDisponibles = [];
        this.contratosAsignados = [];
        this.contratosPendientes = [];
        for (let i = 0; i < contratos.length; i++) {
            const c = contratos[i];
            this.contratosCards[i] = c;

            // contratos ocupados van a asignados
            if (c.esta_ocupado) {
                // los estudiantes solo ven asignados que les pertenecen

                if (this.rolActual === 'estudiante' && c.pasante_email !== this.perfil.email) {
                    /*         if (this.rolActual === 'estudiante' && c.pasante_email !== this.usuario.email) { */
                    continue;
                }
                /* viejo método if (this.usuario?.rol === 'estudiante' && c.pasante_email !== this.usuario.email) {
                  continue;
                } */
                this.contratosAsignados.push(c);
                continue;
            }

            // normalizar postulaciones a array de strings (puede venir como string con comas o como array)
            let postulacionesArr: string[] = [];
            if (typeof (c.postulaciones as any) === 'string') {
                postulacionesArr = ((c.postulaciones as unknown) as string).split(',').map((s: string) => s.trim()).filter((s: string) => s.length > 0);
            } else if (Array.isArray(c.postulaciones)) {
                postulacionesArr = c.postulaciones as unknown as string[];
            }

            /* const userEmail = this.usuario?.email; */
            const userEmail = this.perfil.email;
            if (userEmail && postulacionesArr.includes(userEmail)) {
                this.contratosPendientes.push(c);
            } else {
                this.contratosDisponibles.push(c);
            }
        }

        // copia para filtros
        this.contratosDisponiblesCopia = [...this.contratosDisponibles];

        // Auto-seleccionar / re-sincronizar el contrato del panel derecho.
        // Si ya había uno seleccionado, intentamos mantener el mismo (por id)
        // — importante porque al recargar todosLosContratos se crean objetos nuevos
        // y la referencia anterior queda huérfana. Si no aparece (filtrado), usamos
        // el primer contrato visible.
        const previo = this.contratoAMostrarDetail;
        const visibles = [...this.contratosDisponibles, ...this.contratosPendientes, ...this.contratosAsignados];
        let nuevoSeleccionado = previo ? visibles.find(c => c.id === previo.id) : undefined;

        if (!nuevoSeleccionado && this.pendingSelectContratoId) {
            nuevoSeleccionado = visibles.find(c => c.id === this.pendingSelectContratoId);
            this.pendingSelectContratoId = undefined;
        }

        if (!nuevoSeleccionado) {
            nuevoSeleccionado = visibles[0];
        }

        if (nuevoSeleccionado) {
            this.contratoAMostrarDetail = nuevoSeleccionado;
            this.mostrandoContratoDetail = true;
        } else {
            this.contratoAMostrarDetail = undefined;
            this.mostrandoContratoDetail = false;
        }
    }

    toggleMuestraContratoDetail = (): void => {
        this.mostrandoContratoDetail = !this.mostrandoContratoDetail
    }

    setContratoAMostrar = (contrato: Contrato) => {
        this.contratoAMostrarDetail = contrato;
        this.mostrandoContratoDetail = true;
    }

    // recarga la lista cuando un contrato ha sido asignado en el detalle
    onContratoAssigned(contrato: Contrato | null): void {
        // volver a pedir los contratos
        this.mostrarTodosLosContratos();
        // actualizar el detalle mostrado si nos trajeron el contrato actualizado
        if (contrato) {
            this.contratoAMostrarDetail = contrato;
            this.mostrandoContratoDetail = true;
        } else {
            this.contratoAMostrarDetail = undefined;
            this.mostrandoContratoDetail = false;
        }
    }

    // scroll a una sección por id 
    scrollToSection(sectionId: string): void {
        try {
            const el = document.getElementById(sectionId);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {

                this.viewportScroller.scrollToPosition([0, 0]);
            }
        } catch (err) {
            console.error('Error scrolling to section', err);
        }
    }

    /* cuando se abre una tarjeta de detalle de contrato, se scrollea la view */
    scrollToDetail(): void {
        try {
            this.viewportScroller.scrollToPosition([0, 0]);
            //this.viewportScroller.scrollToPosition([0, document.body.scrollHeight]);
        } catch (err) {
            console.error('Error scrolling to bottom:', err);
        }
    }

    /** Convierte un valor que puede venir como string CSV, array o null en array de strings limpios. */
    private toArray(value: unknown): string[] {
        if (!value) return [];
        if (Array.isArray(value)) {
            return value.map(v => String(v).trim()).filter(v => v.length > 0);
        }
        if (typeof value === 'string') {
            return value.split(',').map(s => s.trim()).filter(s => s.length > 0);
        }
        return [];
    }
}
