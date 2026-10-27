export class Proyecto {
    id?: string;
    nombre?: string;
    description?: string;
    info_link?: string;
    buscando_devs: boolean = true;
    contratos?: string[];
    id_gerente?: string;
    email_gerente?: string;
}

export class ProyectoResponse {
    message?: string;
    count?: number;
    data: Proyecto[] = [];
}