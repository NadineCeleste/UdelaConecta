import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, lastValueFrom } from 'rxjs';
import { environment } from '../environments/environment';

export interface Portfolio {
  id: number;
  titulo1?: string;
  titulo2?: string;
  titulo3?: string;
  descripcion1?: string;
  descripcion2?: string;
  descripcion3?: string;
  repositorio1?: string;
  repositorio2?: string;
  repositorio3?: string;
  imagenes1?: string[];   // hasta 3 URLs
  imagenes2?: string[];
  imagenes3?: string[];
}

@Injectable({ providedIn: 'root' })
export class PortfolioService {
  private apiUrl = environment.apiUrl;
  //private apiUrl = 'http://127.0.0.1:3000/api/';
  private bucketUrl = environment.bucketUrl;

  constructor(private http: HttpClient) { }

  getPortfolioByEmail(email: string): Observable<{ message: string; data: Portfolio }> {
    return this.http.get<{ message: string; data: Portfolio }>(`${this.apiUrl}portfolio/${email}`);
  }

  async existsPortfolio(email: string): Promise<boolean> {
    try {
      const res = await lastValueFrom(this.getPortfolioByEmail(email));
      return res.data && (res.data.id != null || res.data.titulo1 != null);
    } catch {
      return false;
    }
  }

  // Crear/actualizar portfolio 
  createPortfolio(email: string, portfolioData: any): Observable<any> {
    // Asegurar que cada array de imágenes tenga exactamente 3 elementos (strings vacíos si faltan)
    const data = {
      ...portfolioData,
      imagenes1: this.normalizeImagesArray(portfolioData.imagenes1),
      imagenes2: this.normalizeImagesArray(portfolioData.imagenes2),
      imagenes3: this.normalizeImagesArray(portfolioData.imagenes3)
    };
    return this.http.post(`${this.apiUrl}createportfolio/${email}`, data);
  }

  private normalizeImagesArray(images: string[] = []): string[] {
    const arr = images ? [...images] : [];
    while (arr.length < 3) arr.push('');
    return arr.slice(0, 3);
  }

  //  imagen a S3 y devolver URL pública
  async uploadImage(file: File): Promise<string> {
    const key = `portfolios/${Date.now()}_${file.name.replace(/\s/g, '_')}`;
    const uploadUrl = `${this.bucketUrl}/${key}`;

    const response = await fetch(uploadUrl, {
      method: 'PUT',
      body: file,
      headers: { 'Content-Type': file.type }
    });

    if (!response.ok) {
      throw new Error(`Error al subir imagen: ${response.statusText}`);
    }
    return uploadUrl; // URL pública de la imagen
  }

    deletePortfolio(email: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}deleteportfolio/${email}`);
  }


  /**
   * Barre los 9 casilleros de imágenes de un portfolio y elimina de S3 
   * todas aquellas URLs que no estén vacías.
   * @param portfolio Objeto completo de Portfolio a limpiar
   */
  async deleteAllImagesFromPortfolio(portfolio: any): Promise<void> {
    const deletePromises: Promise<void>[] = [];

    // Definimos las propiedades de tipo array que contienen las imágenes
    const bloques: ('imagenes1' | 'imagenes2' | 'imagenes3')[] = ['imagenes1', 'imagenes2', 'imagenes3'];

    for (const bloque of bloques) {
      const arrayImagenes = portfolio[bloque];

      if (arrayImagenes && Array.isArray(arrayImagenes)) {
        for (const url of arrayImagenes) {
          // Filtramos: Solo si tiene contenido y es un string válido iniciamos el borrado
          if (url && url.trim() !== '') {
            deletePromises.push(this.deleteImage(url));
          }
        }
      }
    }

    if (deletePromises.length === 0) {
      console.log('No había imágenes cargadas en el portfolio para eliminar.');
      return;
    }

    try {
      // Ejecuta todas las solicitudes DELETE en paralelo
      await Promise.all(deletePromises);
      console.log(`Se eliminaron con éxito las ${deletePromises.length} imágenes encontradas en S3.`);
    } catch (error) {
      console.error('Al menos una de las imágenes falló al eliminarse de S3:', error);
      // Re-lanzamos para que el componente sepa que el borrado no fue 100% exitoso
      throw error;
    }
  }

  /**
   * Elimina una única imagen de S3 mediante Fetch DELETE (Auxiliar)
   */
  async deleteImage(imageUrl: string): Promise<void> {
    try {
      const response = await fetch(imageUrl, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error(`Error HTTP de S3: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error(`Error al borrar la URL: ${imageUrl}`, error);
      throw error; // Es clave relanzarlo para que Promise.all se entere del fallo
    }
  }

  updatePortfolio(email: string, portfolioData: any): Observable<any> {
        
      // Validación de seguridad
      if (!email) {
        console.error("Faltan datos críticos. Email: ", email);
        throw new Error("No se puede actualizar sin email");
      }
      const url = `${this.apiUrl}updateportfolio/${email}`;
      //console.log("URL: ", url)
      //console.log("data: ", portfolioData)
      return this.http.put<any>(url, portfolioData)
      //lo que sigue es cómo está handleado en la edición de usuarios:
      /* .pipe(
            tap(() => {
              // Actualiza el estado local para que los cambios se vean al instante
              // const current = this.getUserProfileValue(); 
              const current = this.userProfileSubject.value;
              this.setUserProfile({ ...current, ...userData });
            })
          ); */
    }


}