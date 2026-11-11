import { Component, EventEmitter, Input, Output } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import {
  Contrato,
  Orientacion,
  ResultadoCompatibilidad,
  ResultadoPostulante,
} from '../../models/contrato';
import { CommonModule } from '@angular/common';
import { ContratoService } from '../../servicios/contrato';
import { Router } from '@angular/router';
import { AlertService } from '../../servicios/alertService';

@Component({
  selector: 'app-contrato-detail',
  imports: [CommonModule],
  templateUrl: './contrato-detail.html',
  styleUrl: './contrato-detail.css'
})
export class ContratoDetail {

  @Input() contrato?: Contrato;
  //@Output() contratoChange = new EventEmitter<Contrato>;

  @Output() contratoAssigned = new EventEmitter<Contrato | null>();
  @Output() orientacionActualizada = new EventEmitter<{ contratoId: number; orientacion: Orientacion }>();

  @Input() email: string | undefined;
  @Input() rol: string | undefined;

  // Informe determinista y orientación de la postulación del estudiante autenticado.
  @Input() miResultado?: ResultadoCompatibilidad;
  @Input() orientacion?: Orientacion;
  // Informe determinista de cada postulante, solo para la empresa dueña de la oferta.
  @Input() resultadosPostulantes?: ResultadoPostulante[];

  modalVisible = false;
  emailSeleccionado: string | null = null;
  generandoOrientacion = false;

  constructor(
    private route: ActivatedRoute,
    private _apiService: ContratoService,
    private router: Router,
    private alertService: AlertService,
  ) { }

  abrirModal(email: string) {
    this.emailSeleccionado = email;
    this.modalVisible = true;
  }

  cerrarModal() {
    this.modalVisible = false;
    this.emailSeleccionado = null;
  }

  ngOnInit(): void {

  }

  get yaPostulado(): boolean {
    if (!this.email) return false;
    return this.postulacionesNormalizadas.includes(this.email);
  }

  get postulanteSeleccionadoInfo(): ResultadoPostulante | undefined {
    if (!this.emailSeleccionado) return undefined;
    return (this.resultadosPostulantes || []).find(p => p.email === this.emailSeleccionado);
  }

  resultadoDePostulante(email: string): ResultadoCompatibilidad | undefined {
    return (this.resultadosPostulantes || []).find(p => p.email === email)?.resultado;
  }

  resumenRequisitos(resultado?: ResultadoCompatibilidad): string {
    if (!resultado) return 'Sin requisitos cargados';
    if (resultado.sin_requisitos) return 'La oferta no especificó requisitos';
    return `Cumplís ${resultado.total_compatibles} de ${resultado.total_requisitos} requisitos (${resultado.coincidencia}%)`;
  }

  nivelCoincidencia(resultado?: ResultadoCompatibilidad): string {
    const nivel = resultado?.nivel;
    if (nivel === 'alta') return 'Coincidencia alta';
    if (nivel === 'media') return 'Coincidencia media';
    if (nivel === 'baja') return 'Coincidencia baja';
    return 'Sin requisitos para comparar';
  }

  etiquetaEstado(estado: string): string {
    const etiquetas: Record<string, string> = {
      cumple: 'Cumple',
      falta: 'A capacitar',
      parcial: 'A reforzar',
      se_aprende: 'Se aprende en el puesto',
      blanda: 'A evaluar en entrevista',
    };
    return etiquetas[estado] || estado;
  }

  generarOrientacion(): void {
    const contratoId = this.contrato?.id;
    if (!contratoId || this.generandoOrientacion) return;
    this.generandoOrientacion = true;
    this._apiService.pedirOrientacion(contratoId).subscribe({
      next: (res) => {
        this.orientacion = res.data;
        this.generandoOrientacion = false;
        this.alertService.success('Orientación actualizada');
        if (this.orientacion) {
          this.orientacionActualizada.emit({ contratoId, orientacion: this.orientacion });
        }
      },
      error: (err) => {
        this.generandoOrientacion = false;
        this.alertService.error(
          err?.error?.detail || 'No se pudo generar la orientación. Probá de nuevo en unos minutos.'
        );
      }
    });
  }

  asignarPostulante() {
    if (!this.emailSeleccionado || !this.contrato?.id) return;
    console.log("Email que envío:", this.emailSeleccionado);

    this._apiService.asignarPostulante(
      this.contrato.id.toString(),
      this.emailSeleccionado
    )
      .subscribe({
        next: (res) => {
          this.contrato = res.data[0];
          this.contratoAssigned.emit(this.contrato ?? null);
          this.cerrarModal();
          this.alertService.success('Postulante asignado con éxito');
        },
        error: (e) =>{
          console.log(e);
          this.alertService.error('Error al asignar el postulante, '+ e);
        } 
      });
  }

  postularse(contrato: Contrato, email: string) {
    // Una sola llamada: el servidor agrega el email y marca tiene_postulaciones (B-05)
    this._apiService.postularseAContrato(contrato.id!.toString(), email).subscribe({
      next: res => {
        this.contrato = res.data;
        this.alertService.success('Postulación realizada con éxito');
      },
      error: (err) => {
        console.error("Error al postular: ", err);
        this.alertService.error(err?.error?.detail || 'Error al realizar la postulación');
      }
    });
  }

  get postulacionesNormalizadas(): string[] {
    const raw = this.contrato?.postulaciones as unknown;

    if (!raw) return [];

    // Puede venir como array (ya normalizado en el padre) o como string CSV (legacy).
    if (Array.isArray(raw)) {
      return (raw as unknown[])
        .map(s => String(s).trim())
        .filter(s => s.length > 0);
    }

    if (typeof raw === 'string') {
      return raw
        .split(',')
        .map(s => s.trim())
        .filter(s => s.length > 0);
    }

    return [];
  }

  verPerfilPostulante(): void {
    this.router.navigate(['/profile', this.emailSeleccionado]);
  }

}
