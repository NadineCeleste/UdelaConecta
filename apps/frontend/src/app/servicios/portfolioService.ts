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

  // fetch no pasa por el interceptor de HttpClient: el token se agrega a mano
  private authHeaders(): Record<string, string> {
    const token = localStorage.getItem('auth_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  getPortfolioByEmail(email: string): Observable<{ message: string; data: Portfolio }> {
    return this.http.get<{ message: string; data: Portfolio }>(`${this.apiUrl}portfolio/${encodeURIComponent(email)}`);
  }

  async existsPortfolio(email: string): Promise<boolean> {
    try {
      const res = await lastValueFrom(this.getPortfolioByEmail(email));
      return res.data && (res.data.id != null || res.data.titulo1 != null);
    } catch (error: any) {
      // Solo el 404 significa "no tiene"; los demás errores se propagan (E-24)
      if (error?.status === 404) return false;
      throw error;
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
    return this.http.post(`${this.apiUrl}createportfolio/${encodeURIComponent(email)}`, data);
  }

  private normalizeImagesArray(images: string[] = []): string[] {
    const arr = images ? [...images] : [];
    while (arr.length < 3) arr.push('');
    return arr.slice(0, 3);
  }

  //  imagen a S3 y devolver URL pública
  async uploadImage(file: File): Promise<string> {
    // Solo caracteres seguros en la URL; el servidor exige extensión png/jpg/jpeg/gif/webp
    const key = `portfolios/${Date.now()}_${file.name.replace(/[^A-Za-z0-9._-]/g, '_')}`;
    const uploadUrl = `${this.bucketUrl}/${key}`;

    const response = await fetch(uploadUrl, {
      method: 'PUT',
      body: file,
      headers: { 'Content-Type': file.type, ...this.authHeaders() }
    });

    if (!response.ok) {
      throw new Error(`Error al subir imagen: ${response.statusText}`);
    }
    return uploadUrl; // URL pública de la imagen
  }

    deletePortfolio(email: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}deleteportfolio/${encodeURIComponent(email)}`);
  }


  /**
   * Elimina una única imagen de S3 mediante Fetch DELETE (Auxiliar)
   */
  async deleteImage(imageUrl: string): Promise<void> {
    try {
      const response = await fetch(imageUrl, {
        method: 'DELETE',
        headers: this.authHeaders()
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
      const url = `${this.apiUrl}updateportfolio/${encodeURIComponent(email)}`;
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