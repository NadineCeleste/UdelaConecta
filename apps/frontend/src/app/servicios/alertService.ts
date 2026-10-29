import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

export type AlertType = 'success' | 'error' | 'info' | 'warning' | 'confirm';

export interface AlertMessage {
    id: number;
    type: AlertType;
    title?: string;
    message: string;
    timeout?: number;
    resolve?: (value: boolean) => void; // SOLO para confirm
}

@Injectable({ providedIn: 'root' })
export class AlertService {
    private counter = 0;
    private alertSubject = new Subject<AlertMessage>();
    alert$ = this.alertSubject.asObservable();

    show(type: AlertType, message: string, title = '', timeout = 3500) {
        this.alertSubject.next({
            id: ++this.counter,
            type,
            title,
            message,
            timeout,
        });
    }

    success(message: string, title = 'Éxito', timeout = 3500) {
        this.show('success', message, title, timeout);
    }

    error(message: string, title = 'Error', timeout = 4500) {
        this.show('error', message, title, timeout);
    }

    info(message: string, title = 'Info', timeout = 3500) {
        this.show('info', message, title, timeout);
    }

    warning(message: string, title = 'Atención', timeout = 4000) {
        this.show('warning', message, title, timeout);
    }

    confirm(message: string, title = 'Confirmar'): Promise<boolean> {
        return new Promise((resolve) => {
            this.alertSubject.next({
                id: ++this.counter,
                type: 'confirm',
                title,
                message,
                resolve,
            });
        });
    }
}