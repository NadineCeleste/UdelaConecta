import { Component, EventEmitter, Input, Output } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Contrato } from '../../models/contrato';
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

  @Input() email: string | undefined;
  @Input() rol: string | undefined;

  modalVisible = false;
  emailSeleccionado: string | null = null;

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
