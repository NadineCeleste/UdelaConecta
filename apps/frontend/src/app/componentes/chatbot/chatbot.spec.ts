import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';

import { Chatbot } from './chatbot';
import { ChatService } from '../../servicios/chat.service';

describe('Chatbot', () => {
  let component: Chatbot;
  let fixture: ComponentFixture<Chatbot>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Chatbot],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ChatService, useValue: { enviar: () => of('Respuesta de prueba') } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Chatbot);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('arranca cerrado y con el saludo', () => {
    expect(component.abierto()).toBeFalse();
    expect(component.mensajes().length).toBe(1);
    expect(component.mensajes()[0].autor).toBe('bot');
  });

  it('abre y cierra el panel', fakeAsync(() => {
    component.alternar();
    tick();
    expect(component.abierto()).toBeTrue();
    component.cerrar();
    expect(component.abierto()).toBeFalse();
  }));

  it('envía el mensaje y agrega la respuesta', fakeAsync(() => {
    component.enviar('¿Qué ofertas hay?');
    tick();
    const mensajes = component.mensajes();
    expect(mensajes.length).toBe(3);
    expect(mensajes[1]).toEqual(jasmine.objectContaining({ autor: 'usuario', texto: '¿Qué ofertas hay?' }));
    expect(mensajes[2]).toEqual(jasmine.objectContaining({ autor: 'bot', texto: 'Respuesta de prueba' }));
    expect(component.escribiendo()).toBeFalse();
  }));

  it('no envía mensajes vacíos', () => {
    component.enviar('   ');
    expect(component.mensajes().length).toBe(1);
  });
});
