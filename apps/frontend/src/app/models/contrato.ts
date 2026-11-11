export class Requisito {
    nombre: string = '';
    nivel_minimo?: 'principiante' | 'intermedio' | 'avanzado';
    exigencia?: 'excluyente' | 'deseable' | 'se_aprende';
    tipo?: 'tecnica' | 'blanda';
}

export interface ItemChecklist {
    nombre: string;
    estado: 'cumple' | 'falta' | 'parcial' | 'se_aprende' | 'blanda';
    nivel_minimo?: string;
    nivel_declarado?: string | null;
}

export class ResultadoCompatibilidad {
    coincidencia: number = 0;
    nivel: string = '';
    total_requisitos: number = 0;
    total_compatibles: number = 0;
    sin_requisitos: boolean = false;
    compatibles: any[] = [];
    a_capacitar: any[] = [];
    se_aprenden: string[] = [];
    blandas: string[] = [];
    checklist: ItemChecklist[] = [];
    requisitos_invalidos: any[] = [];
}

export class Orientacion {
    texto: string = '';
    estado: 'pendiente' | 'generado' | 'fallback' = 'pendiente';
    modelo?: string;
    actualizado_en?: string;
}

export class Contrato {
    id?: number;
    tipo?: string;
    titulo?: string;
    descripcion?: string;
    tiene_postulaciones?: boolean;
    postulaciones?: string[];
    esta_ocupado?: boolean;
    pasante_email?: string;
    proyecto_id?: string;
    start_date?: string;
    end_date?: string;
    modalidad?: string;               // 'remoto' | 'presencial' | 'hibrido'
    seniority_deseado?: string[];      // ['Trainee','Junior','Semisenior','Senior']
    requisitos?: Requisito[];
    mi_resultado?: ResultadoCompatibilidad;
    resultados_postulantes?: ResultadoPostulante[];
}

export interface ResultadoPostulante {
    email: string;
    nombre?: string;
    resultado: ResultadoCompatibilidad;
}

export class ContratoResponse {
    message?: string;
    count?: number;
    data: Contrato[] = [];
}
export class PostulacionResponse {
    message?: string;
    data?: Contrato;
}