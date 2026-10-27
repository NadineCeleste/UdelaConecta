import { Component } from '@angular/core';
import { FormsModule, NgForm } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ContratoService } from '../../servicios/contrato';
import { Contrato } from '../../models/contrato';
import { AlertService } from '../../servicios/alertService';


@Component({
  selector: 'app-formcreatecontract',
  imports: [FormsModule, CommonModule],
  templateUrl: './formcreatecontract.html',
  styleUrl: './formcreatecontract.css',
})
export class Formcreatecontract {

  constructor(
    private _apiService: ContratoService,
    private router: Router,
    private route: ActivatedRoute,
    private alertService: AlertService
  ) { }

  espost = false;
  esedit = true;
  proyecto: any;

  contrato: Contrato = {
    tipo: "",
    titulo: "",
    descripcion: "",
    tiene_postulaciones: false,
    //postulaciones: [""],
    esta_ocupado: false,
    pasante_email: "",
    proyecto_id: "",
    modalidad: "",
    seniority_deseado: [],
    start_date: "",
    end_date: ""
  }

  ngOnInit(): void {
    /* const pid = this.route.snapshot.paramMap.get('project_id') anterior método */
    const proyecto_id = this.route.snapshot.paramMap.get('id')
    const proyecto_nombre = this.route.snapshot.paramMap.get('nombre')
    this.proyecto = { nombre: proyecto_nombre }
    this.contrato.proyecto_id = proyecto_id!

  }

  cancelar(): void {
    this.router.navigate(['/profile'], { queryParams: { tab: 'ofertas' } });
  }

  // probablemente por project id const email = this.route.snapshot.paramMap.get('email');
  //console.log(email)
  /* if (email) {
    // Llamás al servicio para traer el proyecto y precargarlo
    this._apiService.getProyectoPorEmail(email).subscribe({
      next : (res) => {
        console.log("listo para editar proyecto", this.proyecto)
        this.proyecto = res.data[0]
      }, 
      error: (err) => console.error('Error al cargar proyecto', err)
    });
  } else {
    this.espost = true;
    this.esedit = false;
  } */

  toggleSeniority(valor: string) {
    if (this.contrato.seniority_deseado) {
      const index = this.contrato.seniority_deseado.indexOf(valor);
      if (index === -1) {
        // Si no existe, lo agregamos
        this.contrato.seniority_deseado.push(valor);
      } else {
        // Si ya existe, lo quitamos
        this.contrato.seniority_deseado.splice(index, 1);
      }
    }

  }

  estaSeleccionado(valor: string): boolean {
    if (this.contrato.seniority_deseado) {
      return this.contrato.seniority_deseado.includes(valor);
    } else {
      return false /* <- el flujo nunca debería llegar aquí */
    }
  }


  enviar(form: NgForm) {
    if (form.invalid) {
      return;
    }

    if (!this.contrato.start_date) {
      this.contrato.start_date = new Date().toISOString().split('T')[0];
    }

    const dataParaEnviar = {
      ...this.contrato,
    };

    //console.log("contrato:", this.contrato)

    this._apiService.postContrato(dataParaEnviar).subscribe({
      next: (res) => {
        console.log(res.message)
        this.router.navigate(['/contratos']);
        this.alertService.success('Contrato creado con éxito');
      },
      error: (error: string) => {
        console.log(error)
        this.alertService.error('Error al crear el contrato');
      }
    });

  }

}