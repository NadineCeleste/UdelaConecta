import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Portfolio, PortfolioService } from '../../servicios/portfolioService';
import { AlertService } from '../../servicios/alertService';

@Component({
  selector: 'app-portfolio-component',
  imports: [CommonModule, FormsModule],
  templateUrl: './portfolio-component.html',
  styleUrl: './portfolio-component.css',
})
export class PortfolioComponent implements OnInit {
  @Input() emailDesarrollador: string = '';

  portfolio: Portfolio | null = null;
  mostrarFormulario = false;
  formularioEsEdicion = false;
  cargando = false;
  guardando = false;
  formData: any = {
    titulo1: '', descripcion1: '', repositorio1: '', imagenes1: [] as string[], files1: [] as File[],
    titulo2: '', descripcion2: '', repositorio2: '', imagenes2: [] as string[], files2: [] as File[],
    titulo3: '', descripcion3: '', repositorio3: '', imagenes3: [] as string[], files3: [] as File[]
  };

  // Previsualización de imágenes seleccionadas
  previews: { [key: string]: string[] } = { imagenes1: [], imagenes2: [], imagenes3: [] };

  constructor(
    private portfolioService: PortfolioService,
    private alertService: AlertService
  ) { }

  async ngOnInit() {
    if (!this.emailDesarrollador) return;
    await this.cargarPortfolio();
  }

  async cargarPortfolio() {
    this.cargando = true;
    try {
      const res = await this.portfolioService.getPortfolioByEmail(this.emailDesarrollador).toPromise();
      if (res?.data && (res.data.id || res.data.titulo1)) {
        this.portfolio = res.data;
      } else {
        this.portfolio = null;
      }
    } catch (error) {
      this.portfolio = null;
    } finally {
      this.cargando = false;
    }
  }

  abrircrearPortfolio() {
    // Cargar datos existentes en el formulario
    this.formData = {
      titulo1: this.portfolio?.titulo1 || '',
      descripcion1: this.portfolio?.descripcion1 || '',
      repositorio1: this.portfolio?.repositorio1 || '',
      imagenes1: this.portfolio?.imagenes1 || [],
      files1: [],
      titulo2: this.portfolio?.titulo2 || '',
      descripcion2: this.portfolio?.descripcion2 || '',
      repositorio2: this.portfolio?.repositorio2 || '',
      imagenes2: this.portfolio?.imagenes2 || [],
      files2: [],
      titulo3: this.portfolio?.titulo3 || '',
      descripcion3: this.portfolio?.descripcion3 || '',
      repositorio3: this.portfolio?.repositorio3 || '',
      imagenes3: this.portfolio?.imagenes3 || [],
      files3: []
    };
    // Limpiar previsualizaciones
    this.previews = { imagenes1: [], imagenes2: [], imagenes3: [] };
    this.mostrarFormulario = true;
    //esto no debería ser necesario pero por las dudas...
    this.formularioEsEdicion = false;
  }

  abrireditarPortfolio() {
    // Cargar datos existentes en el formulario
    this.formData = {
      titulo1: this.portfolio?.titulo1 || '',
      descripcion1: this.portfolio?.descripcion1 || '',
      repositorio1: this.portfolio?.repositorio1 || '',
      imagenes1: this.portfolio?.imagenes1 || [],
      files1: [],
      titulo2: this.portfolio?.titulo2 || '',
      descripcion2: this.portfolio?.descripcion2 || '',
      repositorio2: this.portfolio?.repositorio2 || '',
      imagenes2: this.portfolio?.imagenes2 || [],
      files2: [],
      titulo3: this.portfolio?.titulo3 || '',
      descripcion3: this.portfolio?.descripcion3 || '',
      repositorio3: this.portfolio?.repositorio3 || '',
      imagenes3: this.portfolio?.imagenes3 || [],
      files3: []
    };

    // ver imgs existentes (solo las que no son vacías)
    this.previews = {
      imagenes1: (this.portfolio?.imagenes1 || []).filter(img => img && img.trim() !== ''),
      imagenes2: (this.portfolio?.imagenes2 || []).filter(img => img && img.trim() !== ''),
      imagenes3: (this.portfolio?.imagenes3 || []).filter(img => img && img.trim() !== '')
    };
    this.mostrarFormulario = true;
    this.formularioEsEdicion = true;
  }

  async editarPortfolio() {

    if (!this.formData.titulo1?.trim()) {
      this.alertService.warning('El primer proyecto debe tener un título');
      return;
    }

    this.guardando = true;
    try {
  

      // subir imgs solo si hay archivos nuevos
      const imagenesUrls1 = this.formData.files1.length > 0 
        ? await this.subirImagenesProyecto(1,true) 
        : this.formData.imagenes1; // mantener las existentes
      const imagenesUrls2 = this.formData.files2.length > 0 
        ? await this.subirImagenesProyecto(2,true) 
        : this.formData.imagenes2;
      const imagenesUrls3 = this.formData.files3.length > 0 
        ? await this.subirImagenesProyecto(3,true) 
        : this.formData.imagenes3;

      const payload = {
        titulo1: this.formData.titulo1,
        descripcion1: this.formData.descripcion1,
        repositorio1: this.formData.repositorio1,
        imagenes1: imagenesUrls1,
        titulo2: this.formData.titulo2,
        descripcion2: this.formData.descripcion2,
        repositorio2: this.formData.repositorio2,
        imagenes2: imagenesUrls2,
        titulo3: this.formData.titulo3,
        descripcion3: this.formData.descripcion3,
        repositorio3: this.formData.repositorio3,
        imagenes3: imagenesUrls3
      };

      await this.portfolioService.updatePortfolio(this.emailDesarrollador, payload).toPromise();
      this.alertService.success('Portfolio guardado correctamente');
      await this.cargarPortfolio();
      this.mostrarFormulario = false;
      this.formularioEsEdicion = false;
    } catch (error: any) {
      console.error(error);
      this.alertService.error(error?.error?.error || 'Error al guardar el portfolio');
    } finally {
      this.guardando = false;
    }
  }

  // Manejar selección de archivos para un proyecto específico
  onFilesSelected(event: any, projectIndex: number) {
    const files = Array.from(event.target.files) as File[];
    const previewKey = `imagenes${projectIndex}`;
    const currentCount = (this.previews[previewKey] || []).length;
    
    if (currentCount + files.length > 3) {
      this.alertService.warning('Máximo 3 imágenes por proyecto');
      return;
    }

    const key = `files${projectIndex}`;

    if (!this.formData[key]) this.formData[key] = [];
    this.formData[key].push(...files);

    // Agregar nuevas previsualizaciones sin perder las existentes
    for (const file of files) {
      const reader = new FileReader();
      reader.onload = (e) => {
        this.previews[previewKey].push(e.target?.result as string);
      };
      reader.readAsDataURL(file);

    }
  }

  // Eliminar una imagen seleccionada (antes de subir)
  removeSelectedFile(projectIndex: number, fileIndex: number) {
    const key = `files${projectIndex}`;
    const previewKey = `imagenes${projectIndex}`;
    this.formData[key].splice(fileIndex, 1);
    this.previews[previewKey].splice(fileIndex, 1);
  }

  async guardarPortfolio() {
    if (!this.formData.titulo1?.trim()) {
      this.alertService.warning('El primer proyecto debe tener un título');
      return;
    }

    this.guardando = true;
    try {
      // Subir imágenes de cada proyecto a S3 y obtener URLs
      const imagenesUrls1 = await this.subirImagenesProyecto(1);
      const imagenesUrls2 = await this.subirImagenesProyecto(2);
      const imagenesUrls3 = await this.subirImagenesProyecto(3);

      const payload = {
        titulo1: this.formData.titulo1,
        descripcion1: this.formData.descripcion1,
        repositorio1: this.formData.repositorio1,
        imagenes1: imagenesUrls1,
        titulo2: this.formData.titulo2,
        descripcion2: this.formData.descripcion2,
        repositorio2: this.formData.repositorio2,
        imagenes2: imagenesUrls2,
        titulo3: this.formData.titulo3,
        descripcion3: this.formData.descripcion3,
        repositorio3: this.formData.repositorio3,
        imagenes3: imagenesUrls3
      };

      await this.portfolioService.createPortfolio(this.emailDesarrollador, payload).toPromise();
      this.alertService.success('Portfolio guardado correctamente');
      await this.cargarPortfolio();
      this.mostrarFormulario = false;
    } catch (error: any) {
      console.error(error);
      this.alertService.error(error?.error?.error || 'Error al guardar el portfolio');
    } finally {
      this.guardando = false;
    }
  }

  private async subirImagenesProyecto(projectIndex: number, conservarExistentes: boolean = true): Promise<string[]> {
    const filesKey = `files${projectIndex}`;
    const files = this.formData[filesKey] || [];
    const existingImages = this.formData[`imagenes${projectIndex}`] || [];

    // Subir solo los archivos nuevos
    const newUrls: string[] = [];
    for (const file of files) {
      const url = await this.portfolioService.uploadImage(file);
      newUrls.push(url);
    }

    let combined: string[];
    if (conservarExistentes) {
      // Filtrar URLs existentes no vacías
      const existingNonEmpty = existingImages.filter((url: string) => url && url.trim() !== '');
      combined = [...existingNonEmpty, ...newUrls];
    } else {
      combined = newUrls;
    }

    // retorna siempre un array de 3 elementos (los que faltan son vacíos)
    const result = combined.slice(0, 3);
    while (result.length < 3) result.push('');
    return result;
  }


  async eliminarTodoElPortfolio() {

    // uso el alert service que cree
    const confirmado = await this.alertService.confirm(
      '¿Estás seguro de que querés borrar todo el portfolio y sus imágenes asociadas?',
      'Eliminar portfolio'
    );

    if (!confirmado) return;
    
    try {

      const payload = {
        imagenes1: this.portfolio?.imagenes1 || [],
        imagenes2: this.portfolio?.imagenes2 || [],
        imagenes3: this.portfolio?.imagenes3 || [],
      };

      // 1. Limpieza física en AWS S3 de los strings que tengan URLs
      await this.portfolioService.deleteAllImagesFromPortfolio(payload);

      // 2. Procede con la lógica para eliminar el Portfolio de la Base de Datos
      //console.log('Paso 1 completado. Ahora borrando datos de la BD...');

      this.portfolioService.deletePortfolio(this.emailDesarrollador).subscribe({
        next: (res) => {
          console.log('Portfolio eliminado de la base de datos con éxito');
          // limpia la vista
          this.cargarPortfolio();
        },
        error: (dbErr) => {
          console.error('Las imágenes se borraron de S3, pero falló la Base de Datos:', dbErr);
          this.alertService.error('Se borraron las imágenes pero hubo un error al actualizar los datos.');
        }
      });

    } catch (s3Error) {
      // Si S3 falló, el código saltó directo acá. La línea de la BBDD nunca se ejecutó.
      console.error('Operación cancelada. Falló el borrado de imágenes en S3:', s3Error);
      this.alertService.error('No se pudo eliminar el portfolio porque falló la eliminación de archivos en el servidor de AWS.');
    }
    
  }

  cancelarEdicion() {
    this.mostrarFormulario = false;
    this.formularioEsEdicion = false;
    this.formData = {};
    this.previews = { imagenes1: [], imagenes2: [], imagenes3: [] };
  }

  hasImages(images: string[] | undefined): boolean {
    return images ? images.some(img => img && img.trim().length > 0) : false;
  }

  // Método privado que filtra imágenes no vacías
  private filtrarImagenes(imagenes: string[] | undefined): string[] {
    return imagenes?.filter(img => img?.trim()) ?? [];
  }

  // Getters que usan el método privado
  get imagenes1Validas(): string[] {
    return this.filtrarImagenes(this.portfolio?.imagenes1);
  }
  get imagenes2Validas(): string[] {
    return this.filtrarImagenes(this.portfolio?.imagenes2);
  }
  get imagenes3Validas(): string[] {
    return this.filtrarImagenes(this.portfolio?.imagenes3);
  }

  abrirImagen(url: string) {
    if (url && url.startsWith('http')) {
      window.open(url, '_blank');
    }
  }

}

