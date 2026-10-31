import { Component, ElementRef, HostListener, signal, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { AuthService } from '../../servicios/AuthService';
import { ChatService } from '../../servicios/chat.service';

export interface MensajeChat {
  autor: 'usuario' | 'bot';
  texto: string;
  hora: Date;
}

const SUGERENCIAS_INVITADO = ['¿Cómo me registro?', '¿Qué ofertas hay?', '¿Cómo publico una oferta?'];
const SUGERENCIAS_USUARIO = ['¿En qué me postulé?', 'Recomendame ofertas', '¿Cómo mejoro mi perfil?'];

@Component({
  selector: 'app-chatbot',
  imports: [FormsModule],
  templateUrl: './chatbot.html',
  styleUrl: './chatbot.css',
})
export class Chatbot {
  readonly MAX_CARACTERES = 1000;

  abierto = signal(false);
  mensajes = signal<MensajeChat[]>([]);
  escribiendo = signal(false);
  logueado = signal(false);
  // El pulso del botón solo se muestra hasta la primera vez que se abre
  visto = signal(false);
  texto = '';

  private sessionId = crypto.randomUUID();
  private envio?: Subscription;
  private listaMensajes = viewChild<ElementRef<HTMLElement>>('lista');
  private campoTexto = viewChild<ElementRef<HTMLTextAreaElement>>('campo');

  constructor(
    private chatService: ChatService,
    authService: AuthService
  ) {
    // Al entrar o salir de la sesión se empieza una conversación nueva
    authService.userEmail$.pipe(takeUntilDestroyed()).subscribe((email) => {
      this.logueado.set(!!email);
      this.nuevaConversacion();
    });
  }

  get sugerencias(): string[] {
    return this.logueado() ? SUGERENCIAS_USUARIO : SUGERENCIAS_INVITADO;
  }

  // Las sugerencias se ocultan cuando el usuario ya escribió algo
  get mostrarSugerencias(): boolean {
    return !this.escribiendo() && !this.mensajes().some((m) => m.autor === 'usuario');
  }

  alternar(): void {
    this.abierto.update((a) => !a);
    if (this.abierto()) {
      this.visto.set(true);
      setTimeout(() => {
        this.campoTexto()?.nativeElement.focus();
        this.bajarAlFinal();
      });
    }
  }

  @HostListener('document:keydown.escape')
  cerrar(): void {
    this.abierto.set(false);
  }

  nuevaConversacion(): void {
    this.envio?.unsubscribe();
    this.escribiendo.set(false);
    this.sessionId = crypto.randomUUID();
    this.mensajes.set([
      {
        autor: 'bot',
        texto: this.logueado()
          ? '¡Hola de nuevo! Puedo contarte sobre tus postulaciones, ofertas que te pueden interesar o cómo mejorar tu perfil.'
          : '¡Hola! Soy el asistente de Udela Conecta. Te ayudo a encontrar ofertas y a entender cómo funciona la plataforma.',
        hora: new Date(),
      },
    ]);
  }

  enviar(texto: string = this.texto): void {
    const mensaje = texto.trim();
    if (!mensaje || this.escribiendo()) return;

    this.agregar('usuario', mensaje);
    this.texto = '';
    this.escribiendo.set(true);

    this.envio = this.chatService.enviar(mensaje, this.sessionId).subscribe({
      next: (respuesta) => this.agregar('bot', respuesta),
      // El backend manda el motivo en español (límite de mensajes, asistente no disponible…)
      error: (err) =>
        this.agregar(
          'bot',
          err?.error?.detail && typeof err.error.detail === 'string'
            ? err.error.detail
            : 'No pude responder en este momento. Probá de nuevo en unos minutos.'
        ),
      complete: () => this.escribiendo.set(false),
    });
  }

  // Enter envía; Shift+Enter hace un salto de línea
  alPresionarTecla(evento: KeyboardEvent): void {
    if (evento.key === 'Enter' && !evento.shiftKey) {
      evento.preventDefault();
      this.enviar();
    }
  }

  private agregar(autor: MensajeChat['autor'], texto: string): void {
    this.mensajes.update((lista) => [...lista, { autor, texto, hora: new Date() }]);
    if (autor === 'bot') this.escribiendo.set(false);
    setTimeout(() => this.bajarAlFinal());
  }

  private bajarAlFinal(): void {
    const lista = this.listaMensajes()?.nativeElement;
    if (lista) lista.scrollTop = lista.scrollHeight;
  }
}
