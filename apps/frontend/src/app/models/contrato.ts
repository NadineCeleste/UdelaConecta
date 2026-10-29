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