import { Card } from "./card";

export class ContratoCard implements Card {
    id?: number;
    tipo?: string;
    titulo?: string;
    descripcion?: string;
    tiene_postulaciones?: boolean;
    postulaciones?: string[];
    esta_ocupado?: boolean;
    pasante_id?: number;
    start_date?: string;
    end_date?: string;
}